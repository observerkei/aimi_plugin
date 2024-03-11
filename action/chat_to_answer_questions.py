from aimi_plugin.action.type import ActionToolItem


s_action = ActionToolItem(
    call="",
    description="回答问题: 根据问题生成准确的回答. 通过分析得到的请求信息填写回答的内容, 提供足够多的细节. 要对这个问题进行思考. ",
    request="{'type': 'object', 'content': '问题'}",
    execute="system",
)

