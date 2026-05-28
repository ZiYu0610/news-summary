"""调度模块
支持两种运行模式：
1. Python内调度（基于schedule库，适合测试）
2. Windows Task Scheduler（推荐生产使用，提供XML生成）
"""
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ==================== Windows Task Scheduler ====================

def generate_task_xml(project_dir: Path, python_path: Optional[str] = None) -> str:
    """生成Windows任务计划程序XML

    将脚本导入Windows Task Scheduler的方法：
    1. 运行本函数生成XML
    2. 打开"任务计划程序"
    3. 操作 → 导入任务 → 选择此XML
    """
    if python_path is None:
        python_path = sys.executable

    main_script = project_dir / "main.py"
    # Windows下需要确保路径正确
    cmd = f'"{python_path}" "{main_script}"'

    xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>{datetime.now().isoformat()}</Date>
    <Author>AI News Summary</Author>
    <Description>每天早上9点运行AI新闻日报系统</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{datetime.now().strftime("%Y-%m-%d")}T09:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <Enabled>true</Enabled>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <RestartOnFailure>
      <Interval>PT5M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python_path}</Command>
      <Arguments>"{main_script}"</Arguments>
      <WorkingDirectory>{project_dir}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
    return xml


def save_task_xml(output_path: Path):
    """保存Windows Task Scheduler XML文件"""
    project_dir = Path(__file__).parent.parent
    xml = generate_task_xml(project_dir)
    output_path.write_text(xml, encoding="utf-16")
    logger.info(f"任务计划XML已保存到: {output_path}")
    logger.info("使用方式: 打开'任务计划程序' → 导入任务 → 选择此文件")
    return output_path


def install_task_scheduler(project_dir: Path) -> bool:
    """尝试自动注册Windows任务计划

    需要管理员权限运行，否则会失败。
    """
    xml_path = project_dir / "data" / "daily_news_task.xml"
    save_task_xml(xml_path)

    try:
        result = subprocess.run(
            ["schtasks", "/create", "/xml", str(xml_path), "/tn", "AIGC新闻日报"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            logger.info("Windows任务计划注册成功！")
            logger.info("任务名: AIGC新闻日报，每天 09:00 执行")
            return True
        else:
            logger.warning(f"自动注册失败（可能需要管理员权限）: {result.stderr}")
            logger.info(f"请手动导入任务: 使用 {xml_path} 文件")
            return False
    except Exception as e:
        logger.error(f"注册任务计划出错: {e}")
        return False


# ==================== schedule 库调度 ====================

def run_schedule_loop(main_func, time_str: str = "09:00"):
    """使用schedule库运行循环调度

    适合测试和开发环境。
    生产环境建议使用Windows Task Scheduler。
    """
    try:
        import schedule
    except ImportError:
        logger.error("schedule库未安装，请执行: pip install schedule")
        raise

    hour, minute = time_str.split(":")
    schedule.every().day.at(time_str).do(main_func)

    logger.info(f"调度已启动，将在每天 {time_str} 执行日报生成")
    logger.info("保持此窗口运行...")

    # 立即运行一次（可选）
    from config import DATA_DIR
    flag_file = Path(DATA_DIR) / ".first_run"
    if not flag_file.exists():
        logger.info("首次启动，立即执行一次...")
        main_func()
        flag_file.touch()

    while True:
        schedule.run_pending()
        import time
        time.sleep(30)
