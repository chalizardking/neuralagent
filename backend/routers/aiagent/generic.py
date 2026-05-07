from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlmodel import Session, select, and_
from db.database import get_session
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from utils import constants
from botocore.config import Config
from langchain_aws import ChatBedrockConverse
from langchain_openai import AzureChatOpenAI
import json
from utils import ai_prompts
from utils.procedures import CustomError, extract_json, extract_json_array
from dependencies.auth_dependencies import get_current_user_dependency
from db.models import (User, Thread, ThreadStatus, ThreadTask, ThreadTaskStatus, ThreadMessage,
                       ThreadChatType, ThreadChatFromChoices, ThreadTaskPlan, ThreadTaskPlanStatus,
                       PlanSubtask, SubtaskStatus, ThreadTaskMemoryEntry, SubtaskType)
from schemas.aiagent import NextStepRequest, CurrentSubtaskRequestObj
from utils.agentic_tools import run_tool_server_side
from utils import llm_provider


router = APIRouter(
    prefix='/aiagent',
    tags=['aiagent'],
    dependencies=[Depends(get_current_user_dependency)]
)


@router.post('/{tid}/current_subtask')
def current_subtask_request(tid: str, current_subtask_request_obj: CurrentSubtaskRequestObj,
                            db: Session = Depends(get_session), user: User = Depends(get_current_user_dependency)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status == ThreadStatus.WORKING
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    task = db.exec(select(ThreadTask).where(and_(
        ThreadTask.thread_id == tid,
        ThreadTask.status == ThreadTaskStatus.WORKING,
    ))).first()

    if not task:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread has no running task')

    current_plan = db.exec(select(ThreadTaskPlan).where(and_(
        ThreadTaskPlan.thread_task_id == task.id,
        ThreadTaskPlan.status == ThreadTaskPlanStatus.ACTIVE,
    ))).first()

    if not current_plan:
        previous_tasks = db.exec(select(ThreadTask).where(and_(
            ThreadTask.thread.has(Thread.user_id == user.id),
            ThreadTask.thread.has(Thread.status != ThreadStatus.DELETED),
            ThreadTask.status != ThreadTaskStatus.WORKING,
        )).order_by(ThreadTask.created_at.desc()).limit(10)).all()
        previous_tasks_arr = []
        for previous_task in previous_tasks:
            previous_tasks_arr.append({
                'task': previous_task.task_text,
                'status': previous_task.status,
            })

        llm = llm_provider.get_llm(agent='planner', temperature=0.3)

        plan_user_message = [
            {
                'type': 'text',
                'text': f'Current OS: {current_subtask_request_obj.current_os} \n\nCurrent Visible OS Native Interactive Elements: {json.dumps(current_subtask_request_obj.current_interactive_elements)}'
            },
            {
                'type': 'text',
                'text': f'Current Running Apps: {json.dumps(current_subtask_request_obj.current_running_apps)}'
            }
        ]

        if len(previous_tasks_arr) > 0:
            plan_user_message.append({
                'type': 'text',
                'text': f'Previous Tasks (Limited to 10): \n {json.dumps(previous_tasks_arr)}',
            })

        plan_user_message.append({
            'type': 'text',
            'text': f'Task: {task.task_text}'
        })

        plan_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(ai_prompts.PLANNER_AGENT_PROMPT),
            HumanMessage(content=plan_user_message),
        ])

        chain = plan_prompt | llm
        plan_response = chain.invoke({})
        plan_response_data = extract_json(plan_response.content)

        plan = plan_response_data.get('subtasks')

        plan_ai_message = ThreadMessage(
            thread_id=instance.id,
            thread_chat_type=ThreadChatType.PLAN,
            thread_chat_from=ThreadChatFromChoices.FROM_AI,
            text=json.dumps(plan_response_data),
        )
        db.add(plan_ai_message)
        db.commit()
        db.refresh(plan_ai_message)

        current_plan = ThreadTaskPlan(
            thread_task_id=task.id,
        )
        db.add(current_plan)
        db.commit()
        db.refresh(current_plan)

        # ⚡ Bolt Optimization: Batched database insertions to avoid N+1 queries.
        # Impact: Eliminates sequential db.commit() and db.refresh() roundtrips per loop iteration, significantly reducing overall task setup latency.
        subtasks_to_add = [
            PlanSubtask(
                thread_task_plan_id=current_plan.id,
                subtask_text=subtask_item.get('subtask'),
                subtask_type=SubtaskType.DESKTOP,
                ordering=i + 1,
            ) for i, subtask_item in enumerate(plan)
        ]
        if subtasks_to_add:
            db.add_all(subtasks_to_add)
            db.commit()

    current_subtask = db.exec(select(PlanSubtask).where(and_(
        PlanSubtask.status == SubtaskStatus.ACTIVE,
        PlanSubtask.thread_task_plan_id == current_plan.id
    )).order_by(PlanSubtask.ordering.asc())).first()

    if not current_subtask:
        # ⚡ Bolt Optimization: Consolidated sequential updates into a single add_all and commit.
        # Impact: Combines 4 separate database transactions into 1, reducing network overhead and lock contention.
        current_plan.status = ThreadTaskPlanStatus.COMPLETED
        task.status = ThreadTaskStatus.COMPLETED
        instance.status = ThreadStatus.STANDBY

        ai_message = ThreadMessage(
            thread_id=instance.id,
            thread_task_id=task.id,
            thread_chat_type=ThreadChatType.DESKTOP_USE,
            thread_chat_from=ThreadChatFromChoices.FROM_AI,
            text=json.dumps({'actions': [{'action': 'task_completed'}]}),
        )
        db.add_all([current_plan, task, instance, ai_message])
        db.commit()

        return {'action': 'task_completed'}

    return {
        'id': current_subtask.id,
        'subtask_text': current_subtask.subtask_text,
        'subtask_type': current_subtask.subtask_type,
        'status': current_subtask.status,
    }


@router.post('/{tid}/next_step')
def next_step(tid: str, next_step_req: NextStepRequest, db: Session = Depends(get_session),
              user: User = Depends(get_current_user_dependency)):
    instance = db.exec(select(Thread).where(and_(
        Thread.id == tid,
        Thread.user_id == user.id,
        Thread.status == ThreadStatus.WORKING
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    task = db.exec(select(ThreadTask).where(and_(
        ThreadTask.thread_id == tid,
        ThreadTask.status == ThreadTaskStatus.WORKING,
    ))).first()

    if not task:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread has no running task')

    current_plan = db.exec(select(ThreadTaskPlan).where(and_(
        ThreadTaskPlan.thread_task_id == task.id,
        ThreadTaskPlan.status == ThreadTaskPlanStatus.ACTIVE,
    ))).first()

    current_subtask = db.exec(select(PlanSubtask).where(and_(
        PlanSubtask.status == SubtaskStatus.ACTIVE,
        PlanSubtask.thread_task_plan_id == current_plan.id
    )).order_by(PlanSubtask.ordering.asc())).first()
    if not current_subtask or current_subtask.subtask_type != SubtaskType.DESKTOP:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'No Current Desktop Task!')

    if task.extended_thinking_mode is True:
        llm = llm_provider.get_llm(agent='computer_use', temperature=1.0, thinking_enabled=True)
    else:
        llm = llm_provider.get_llm(agent='computer_use', temperature=0.0)

    previous_subtasks = db.exec(select(PlanSubtask).where(and_(
        PlanSubtask.status != SubtaskStatus.ACTIVE,
        PlanSubtask.plan.has(ThreadTaskPlan.thread_task_id == task.id)
    )).order_by(PlanSubtask.ordering.asc())).all()
    previous_subtasks_arr = []
    for previous_subtask in previous_subtasks:
        previous_subtasks_arr.append({
            'subtask_text': previous_subtask.subtask_text,
            'status': previous_subtask.status,
        })

    screenshot_user_message_block = None
    if next_step_req.screenshot_b64:
        screenshot_user_message_block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": next_step_req.screenshot_b64
            }
        }

    action_history = []
    task_previous_messages = db.exec(
        select(ThreadMessage)
        .where(
            and_(
                ThreadMessage.thread_task_id == task.id,
                ThreadMessage.thread_chat_type == ThreadChatType.DESKTOP_USE,
            )
        )
        .order_by(ThreadMessage.created_at.desc())  # Adjust if your timestamp column is named differently
        .limit(5)
    ).all()
    for previous_message in task_previous_messages:
        previous_action_dict = json.loads(previous_message.text)
        # previous_action_dict.pop("current_state", None)
        action_history.append(previous_action_dict)

    if task.needs_memory_from_previous_tasks is True:
        tasks_for_memory = db.exec(select(ThreadTask).where(and_(
            ThreadTask.thread.has(Thread.user_id == user.id),
            ThreadTask.thread.has(Thread.status != ThreadStatus.DELETED),
        )).order_by(ThreadTask.created_at.desc()).limit(5)).all()
        tasks_for_memory_ids = [task.id for task in tasks_for_memory]
        memory_items = db.exec(
            select(ThreadTaskMemoryEntry).where(
                ThreadTaskMemoryEntry.thread_task_id.in_(tasks_for_memory_ids)
            )
        ).all()
    else:
        memory_items = db.exec(select(ThreadTaskMemoryEntry).where(
            ThreadTaskMemoryEntry.thread_task_id == task.id
        )).all()

    memory_items_arr = []
    for memory_item in memory_items:
        memory_items_arr.append({
            'memory_item_text': memory_item.text,
        })

    computer_use_user_message = [
        {
            'type': 'text',
            'text': f'Current Subtask: {current_subtask.subtask_text}'
        },
        {
            'type': 'text',
            'text': f'Current OS: {next_step_req.current_os} \n\nCurrent Visible OS Native Interactive Elements: {json.dumps(next_step_req.current_interactive_elements)}'
        },
        {
            'type': 'text',
            'text': f'Current Running Apps: {json.dumps(next_step_req.current_running_apps)}'
        }
    ]

    if len(memory_items_arr) > 0:
        computer_use_user_message.append({
            'type': 'text',
            'text': f'Stored Memory Items: \n {json.dumps(memory_items_arr)}'
        })
    if len(action_history) > 0:
        computer_use_user_message.append({
            'type': 'text',
            'text': f'Previous Actions: \n {json.dumps(action_history)}'
        })
    if len(previous_subtasks_arr) > 0:
        computer_use_user_message.append({
            'type': 'text',
            'text': f'Previous Subtasks: \n {json.dumps(previous_subtasks_arr)}'
        })
    
    if screenshot_user_message_block:
        computer_use_user_message.append(screenshot_user_message_block)

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=ai_prompts.COMPUTER_USE_SYSTEM_PROMPT),
        HumanMessage(content=computer_use_user_message),
    ])

    chain = prompt | llm
    response = chain.invoke({})

    print('Token Usage: ', response.usage_metadata)

    response_data = None
    if task.extended_thinking_mode is True:
        # ⚡ Bolt Optimization: Batched thinking message insertions.
        # Impact: Prevents N+1 queries by committing all AI thoughts simultaneously instead of one by one.
        thinking_messages_to_add = []
        for response_item in response.content:
            if response_item.get('type') == 'reasoning_content':
                thinking_messages_to_add.append(
                    ThreadMessage(
                        thread_id=instance.id,
                        thread_task_id=task.id,
                        thread_chat_type=ThreadChatType.THINKING,
                        thread_chat_from=ThreadChatFromChoices.FROM_AI,
                        chain_of_thought=response_item.get('reasoning_content', {}).get('text'),
                    )
                )
            elif response_item.get('type') == 'text':
                response_data = extract_json(response_item.get('text'))
        if thinking_messages_to_add:
            db.add_all(thinking_messages_to_add)
            db.commit()
    else:
        response_data = extract_json(response.content)

    ai_message = ThreadMessage(
        thread_id=instance.id,
        thread_task_id=task.id,
        plan_subtask_id=current_subtask.id,
        thread_chat_type=ThreadChatType.DESKTOP_USE,
        thread_chat_from=ThreadChatFromChoices.FROM_AI,
        text=json.dumps(response_data),
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)

    if response_data.get('current_state', {}).get('save_to_memory', False):
        memory_text = response_data['current_state'].get('memory')
        if memory_text:
            memory_entry = ThreadTaskMemoryEntry(
                thread_task_id=task.id,
                text=memory_text,
            )
            db.add(memory_entry)
            db.commit()
            db.refresh(memory_entry)

    # Iterate over all actions
    # ⚡ Bolt Optimization: Consolidated all iterative database operations within the action loop.
    # Impact: Replaces individual loop transaction commits with a single batched commit at the end, dramatically speeding up multi-action processing.
    actions_arr = response_data.get('actions', [])
    objects_to_add = []

    for act in actions_arr:
        action_type = act.get('action')

        if action_type == 'subtask_completed' and len(actions_arr) == 1:
            current_subtask.status = SubtaskStatus.COMPLETED
            objects_to_add.append(current_subtask)

        elif action_type == 'subtask_failed':
            # Mark plan, task, and thread as failed
            current_plan.status = ThreadTaskPlanStatus.FAILED
            objects_to_add.append(current_plan)

            task.status = ThreadTaskStatus.FAILED
            objects_to_add.append(task)

            instance.status = ThreadStatus.STANDBY
            objects_to_add.append(instance)

            ai_message = ThreadMessage(
                thread_id=instance.id,
                thread_task_id=task.id,
                thread_chat_type=ThreadChatType.DESKTOP_USE,
                thread_chat_from=ThreadChatFromChoices.FROM_AI,
                text=json.dumps({'actions': [{'action': 'task_failed'}]}),
            )
            objects_to_add.append(ai_message)

        elif action_type == 'tool_use':
            tool = act['params'].get('tool')
            args = act['params'].get('args', {})

            if tool == 'save_to_memory':
                memory_entry = ThreadTaskMemoryEntry(
                    thread_task_id=task.id,
                    text=args.get('text', ''),
                )
                objects_to_add.append(memory_entry)

            elif tool in ['read_pdf', 'fetch_url', 'summarize_youtube_video']:
                tool_output_text = run_tool_server_side(tool, args)
                memory_entry = ThreadTaskMemoryEntry(
                    thread_task_id=task.id,
                    text=tool_output_text,
                )
                objects_to_add.append(memory_entry)

    if objects_to_add:
        db.add_all(objects_to_add)
        db.commit()

    return response_data
