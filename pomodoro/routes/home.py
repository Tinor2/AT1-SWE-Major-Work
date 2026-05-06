from flask import Blueprint, render_template
from flask_login import login_required, current_user

bp = Blueprint('home', __name__)


@bp.route('/')
@login_required
def index():
    from ..models.list import get_active_list
    from ..models.task import get_tasks_with_time
    active_list = get_active_list(current_user.id)

    tasks = []
    if active_list:
        tasks = get_tasks_with_time(active_list['id'], current_user.id)

    return render_template('home/index.html', active_list=active_list, tasks=tasks)

# Phase 6: Render functions removed - now using Jinja2 templates in home/partials/task_item.html
# The following functions have been deleted:
# - render_task_hierarchy()
# - render_parent_task()
# - render_subtask()
