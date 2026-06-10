"""工作流编排引擎 — DAG 驱动的多步骤任务编排

规划中的模块，将实现：
- 工作流 DAG 定义
- 节点（Agent / Tool）编排
- 条件分支与并行执行
- 执行状态追踪与重试

使用示例（规划）::

    from jinshiagent.workflow import Workflow, Step

    wf = Workflow("数据处理流水线")
    wf.add_step(Step("extract", agent=extractor))
    wf.add_step(Step("transform", agent=transformer, depends_on=["extract"]))
    wf.add_step(Step("load", agent=loader, depends_on=["transform"]))
    result = wf.run(input_data)
"""

__all__ = []
