from aimi_plugin.action.type import ActionToolItem


s_action = ActionToolItem(
    # 这个动作的名称, 默认是文件名
    # 在这里只是起到说明作用
    call="",
    # 当前 action 的描述
    # 说明这个action应该怎么使用
    description="创建模拟对象: 只能用于生成模拟对象, 可同时生成多个对象. "
        f"可以自动补全生成对象所需要的信息. ",
    # 调用接口的时候填写的参数说明
    request={
        "type": "object",
        "mock": [
            {
                "type": "object",
                "description": "生成的其中一个角色相关信息. ",
                "name": "角色的名称: 用英文命名. 不可和其他人重复",
                "expect": "生成期望: 为了解决什么问题生成这个角色. ",
                "capacity": "能力分布: 这个角色具有什么能力",
                "format": "回复格式: 这个角色回复的时候, 会遵循什么格式进行回复, 要同时给出具体的例子才行. "
                    "如 模拟 Shell 时, 我说 'ls /tmp', 那么你回复 '[Shell]\n```shell\n1 2 3\n```'",
            },
        ],
    },
    # 这里指明执行类型
    # system: 系统执行, 会有 chat_from 返回值
    # AI:     AI 执行, 没有 chat_from 返回值
    execute="AI",
)
