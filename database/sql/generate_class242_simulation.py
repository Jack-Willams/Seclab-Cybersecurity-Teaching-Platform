"""生成 242 班模拟学习数据的 SQL 脚本。

设计要点：
- 用固定随机种子，结果可复现
- 每个知识点有不同的班级掌握度，形成红/橙/黄/绿完整分布
- 学生有能力分层（强/中/弱），不是均匀随机
- 错误答案按知识点给出不同的真实误区，不用同一句模板
- 时间跨度 3 周，分多次训练会话
- 部分学生做错后重做（第二次通常答对），形成重做轨迹
"""
import random
import json
from datetime import datetime, timedelta

random.seed(20260808)

USER_SCHEMA = "userservice"
TEACHING_CLASS_ID = 5      # 网安242班
ADMIN_CLASS_ID = 8         # 对应行政班
COURSE_ID = 1              # SQL注入攻击（教师端分析的实验）
PREFIX = "sim242"
NUMERIC_BASE = 92000000
SOURCE = "ai-agent-service"   # 生产来源，画像/能力成长会纳入统计

# user_id -> 姓名（31人，来自 teaching_class_student）
STUDENTS = list(range(92, 123))

# 知识点定义：目标错题率决定饼图颜色
#   >=60% 红(严重错误)  40-59% 橙(重点关注)  20-39% 黄(需要巩固)  <20% 绿(掌握良好)
KNOWLEDGE_POINTS = [
    {
        "id": 401, "module": 4, "task": 1, "difficulty": "hard",
        "desired_rate": 0.68,
        "title": "无空格命令执行排查",
        "stem": "当服务端过滤了空格字符时，攻击者可能使用哪些等价方式构造命令？服务端应当如何正确防御？",
        "reference": "可用 ${IFS}、变量展开、重定向等替代空格；服务端应使用参数化调用与命令白名单，而不是过滤单个字符。",
        "explanation": "shell 存在多种空格等价表达，基于字符过滤的防御必然可绕过，应改为无 shell 的参数数组调用。",
        "correct": [
            "可以用 ${IFS} 或 $IFS$9 代替空格，还有变量展开和重定向也能实现；防御不能靠过滤字符，要用参数化调用加白名单。",
            "空格可以被 ${IFS}、大括号展开、重定向符号替代。正确做法是服务端不拼接 shell 命令，改用参数数组传参并限制可执行命令范围。",
            "常见替代有 ${IFS}、{cat,flag} 这种大括号写法、以及 <> 重定向。根本防御是不走 shell，用白名单校验命令名。",
        ],
        "wrong": [
            "把空格过滤掉就安全了，攻击者没有空格就没法拼命令。",
            "用 %20 编码就能绕过空格过滤，防御的话把 %20 也一起过滤。",
            "可以用 Tab 键代替空格。服务端再把 Tab 也加进黑名单就行了。",
            "只写出了 ${IFS} 这一种，没说服务端该怎么改。",
            "过滤掉分号和管道符就能防止命令注入了。",
        ],
    },
    {
        "id": 501, "module": 5, "task": 1, "difficulty": "hard",
        "desired_rate": 0.5,
        "title": "上传文件类型校验",
        "stem": "结合一次实验现象说明：仅检查 Content-Type 为什么不足以阻止恶意文件上传？请给出两项后端措施。",
        "reference": "Content-Type 可伪造；后端应校验内容特征、重命名文件、隔离存储并禁止执行权限。",
        "explanation": "客户端提供的元数据不可信，需要内容校验与安全存储共同控制。",
        "correct": [
            "Content-Type 由客户端发送，抓包就能改成 image/png。后端要读文件头判断真实类型，并且重命名后存到不可执行的目录。",
            "实验里我用 Burp 把 Content-Type 改成图片就传上去了，说明它不可信。后端应该校验文件内容特征，同时隔离存储并去掉执行权限。",
            "请求头可以任意伪造。两项措施：一是按文件头/魔数校验真实类型，二是随机重命名并存放在 Web 目录之外。",
        ],
        "wrong": [
            "检查文件后缀名就可以了，只允许 jpg 和 png 后缀。",
            "在前端限制上传的文件类型，用户就选不了非法文件。",
            "Content-Type 可以伪造，但没写出后端应该做什么。",
            "把上传的文件改名就行了，改了名就执行不了。",
        ],
    },
    {
        "id": 101, "module": 1, "task": 1, "difficulty": "medium",
        "desired_rate": 0.45,
        "title": "UNION 查询列数判断",
        "stem": "在不知道原查询列数时，如何使用 ORDER BY 确定 UNION SELECT 的列数？",
        "reference": "从 ORDER BY 1 开始递增，首次报错的序号减一即为原查询列数。",
        "explanation": "ORDER BY 引用的列序号超过结果列数时数据库会报错，可据此确定边界。",
        "correct": [
            "从 ORDER BY 1 开始往上试，一直到某个数字开始报错，那个数字减一就是列数。再用 UNION SELECT NULL 补齐同样列数验证一下。",
            "递增 ORDER BY 的序号，首次报错说明超出了列数范围，所以列数等于报错序号减一。",
            "ORDER BY 1、2、3 依次试，假设 ORDER BY 5 报错而 4 正常，那原查询就是 4 列，然后 UNION SELECT NULL,NULL,NULL,NULL 验证。",
        ],
        "wrong": [
            "直接用 UNION SELECT 1,2,3 一个个试，不报错就是对的。",
            "页面上显示了几个字段就是几列。",
            "用 ORDER BY 排序看看结果有没有变化，变了就说明列数对。",
            "只写出了部分步骤，缺少验证依据。",
        ],
    },
    {
        "id": 201, "module": 2, "task": 1, "difficulty": "medium",
        "desired_rate": 0.32,
        "title": "HTML 属性上下文编码",
        "stem": "同一段用户输入分别进入 HTML 文本、标签属性值和 script 块时，输出编码方式有什么不同？",
        "reference": "先判断输出上下文：HTML 文本用实体编码，属性值必须加引号并编码引号字符，script 内需 JS 编码或避免直接拼接。",
        "explanation": "XSS 防御的关键是按输出位置选择编码方式，单一过滤函数无法覆盖所有上下文。",
        "correct": [
            "要看输出到哪里。HTML 文本里用实体编码，属性值要用引号包起来并且把引号转义，脚本里不能直接拼字符串，得用 JSON 序列化。",
            "三个位置编码规则不一样：文本节点做 HTML 实体编码；属性值编码引号并强制加引号；script 块要用 JS 转义，最好完全不拼接。",
            "先判断上下文再选编码。属性值如果不加引号，攻击者不用引号也能注入事件处理器，所以引号和编码要一起做。",
        ],
        "wrong": [
            "统一用 htmlspecialchars 转义一下就行了。",
            "把 <script> 标签过滤掉就能防止 XSS。",
            "对所有输入做一次过滤，输出的时候就不用管了。",
            "只说了要转义，没区分三种上下文。",
        ],
    },
    {
        "id": 301, "module": 3, "task": 1, "difficulty": "medium",
        "desired_rate": 0.26,
        "title": "CSRF Token 会话绑定",
        "stem": "CSRF Token 为什么需要与用户会话绑定并由服务端校验？",
        "reference": "Token 必须与会话绑定并在服务端逐次比对，只在页面放置随机值而不做服务端校验不能形成防护。",
        "explanation": "只在页面放置随机值但不做服务端校验不能形成防护。",
        "correct": [
            "如果不和会话绑定，攻击者自己拿一个合法 token 就能给别人用。必须服务端存一份和当前 session 对应的值，每次提交都比对。",
            "Token 的作用是证明请求来自本站页面。不绑定会话就无法区分是哪个用户的 token，服务端不校验等于没做。",
            "服务端要把 token 和 session 关联存储，收到请求时取出来比对，不一致就拒绝，否则伪造请求照样能通过。",
            "因为 token 要能证明请求发起方持有当前会话，光在表单里放随机数而服务端不验证，攻击者构造一个同样格式的就绕过了。",
        ],
        "wrong": [
            "页面里放一个随机 token 就能防住 CSRF 了。",
            "校验 Referer 头就够了，不需要 token。",
            "只写出了部分步骤，缺少验证依据。",
        ],
    },
    {
        "id": 102, "module": 1, "task": 3, "difficulty": "medium",
        "desired_rate": 0.14,
        "title": "时间盲注基准验证",
        "stem": "在没有任何回显的场景下，如何用时间延迟确认注入点确实存在？",
        "reference": "先用恒真/恒假构造两个基准请求对照响应时间，再加入延时条件观察差异，并排除网络抖动的影响。",
        "explanation": "缺少基准对照时无法区分延迟来自注入还是网络波动。",
        "correct": [
            "先发恒真和恒假两个请求作为基准，记录正常响应时间，再加 SLEEP 看时间差是否稳定复现，多测几次排除网络抖动。",
            "要有对照组。先测正常请求耗时，再构造恒假条件确认不延时，最后恒真加延时看是否稳定变慢，重复几次才能下结论。",
            "单看一次变慢说明不了问题，必须有基准对照并重复验证，确认延迟只在条件为真时出现。",
        ],
        "wrong": [
            "直接加 sleep(5)，页面变慢了就说明有注入。",
            "响应时间超过 5 秒就能确认存在时间盲注。",
        ],
    },
    {
        "id": 601, "module": 6, "task": 1, "difficulty": "easy",
        "desired_rate": 0.1,
        "title": "目录遍历路径归一化",
        "stem": "为什么简单过滤 ../ 字符串不能防止目录遍历？正确的服务端做法是什么？",
        "reference": "编码变形和嵌套写法可绕过字符串过滤；应先对路径做规范化，再校验最终路径是否落在允许的根目录内。",
        "explanation": "路径校验必须在规范化之后进行，否则各种等价写法都能绕过。",
        "correct": [
            "因为 ....// 这种嵌套写法被替换一次之后又变回 ../，URL 编码也能绕。正确做法是先规范化路径，再检查是否还在允许目录下。",
            "字符串替换会被 %2e%2e%2f 或者 ....// 绕过。应该用 realpath 之类先归一化，然后判断结果是不是以允许的根目录开头。",
            "过滤是黑名单思路，等价写法太多。要先把路径解析成绝对路径，再和白名单根目录做前缀比对。",
        ],
        "wrong": [
            "把 ../ 替换成空字符串就可以了。",
            "只允许用户输入文件名，不允许带斜杠。",
        ],
    },
]

# ── XSS与CSRF攻击（course_id = 2）────────────────────────────────
# 平台原本只有 201/301 两个 XSS/CSRF 知识点，饼图太单薄，
# 这里在空闲 id 段补 202/203/302 三个本课程专属知识点（见 NEW_KNOWLEDGE_POINTS）。
XSS_KNOWLEDGE_POINTS = [
    {
        "id": 203, "module": 2, "task": 3, "difficulty": "hard",
        "desired_rate": 0.66,
        "title": "CSP 与 HttpOnly 的防护边界",
        "stem": "开启 HttpOnly 之后是否就不用担心 XSS 了？请说明 HttpOnly 与 CSP 各自能防住什么、防不住什么。",
        "reference": "HttpOnly 只阻止脚本读取 Cookie，不阻止 XSS 执行；CSP 限制脚本来源可降低注入脚本被执行的概率，但配置不当（如 unsafe-inline）会失效。根本仍是输出编码。",
        "explanation": "两者都是纵深防御手段而非根治方案，不能替代按上下文的输出编码。",
        "correct": [
            "不能。HttpOnly 只是让 document.cookie 读不到，攻击者照样能用 XSS 发请求、改页面、钓鱼。CSP 能限制脚本来源，但写了 unsafe-inline 就形同虚设，根本还是要做输出编码。",
            "HttpOnly 防的是 Cookie 被脚本读走，XSS 本身还在。CSP 可以挡掉外部脚本和内联脚本，但配置不严就没用。两者都是补充，不能代替编码。",
            "HttpOnly 只保护 Cookie 这一项，攻击者仍可用受害者身份发起请求。CSP 需要严格禁用 unsafe-inline 才有意义。真正的修复是按输出上下文编码。",
        ],
        "wrong": [
            "开了 HttpOnly 就安全了，脚本读不到 Cookie 就没法攻击。",
            "配置了 CSP 就完全不会有 XSS 了。",
            "HttpOnly 能阻止 XSS 脚本执行。",
            "只说了 HttpOnly 保护 Cookie，没提 CSP 也没说防不住什么。",
        ],
    },
    {
        "id": 201, "module": 2, "task": 1, "difficulty": "medium",
        "desired_rate": 0.48,
        "title": "HTML 属性上下文编码",
        "stem": "同一段用户输入分别进入 HTML 文本、标签属性值和 script 块时，输出编码方式有什么不同？",
        "reference": "先判断输出上下文：HTML 文本用实体编码，属性值必须加引号并编码引号字符，script 内需 JS 编码或避免直接拼接。",
        "explanation": "XSS 防御的关键是按输出位置选择编码方式，单一过滤函数无法覆盖所有上下文。",
        "correct": [
            "要看输出到哪里。HTML 文本里用实体编码，属性值要用引号包起来并且把引号转义，脚本里不能直接拼字符串，得用 JSON 序列化。",
            "三个位置编码规则不一样：文本节点做 HTML 实体编码；属性值编码引号并强制加引号；script 块要用 JS 转义，最好完全不拼接。",
            "先判断上下文再选编码。属性值如果不加引号，攻击者不用引号也能注入事件处理器，所以引号和编码要一起做。",
        ],
        "wrong": [
            "统一用 htmlspecialchars 转义一下就行了。",
            "把 <script> 标签过滤掉就能防止 XSS。",
            "对所有输入做一次过滤，输出的时候就不用管了。",
            "只说了要转义，没区分三种上下文。",
        ],
    },
    {
        "id": 202, "module": 2, "task": 2, "difficulty": "medium",
        "desired_rate": 0.34,
        "title": "存储型与反射型 XSS 的区分",
        "stem": "存储型 XSS 与反射型 XSS 在触发方式和危害范围上有什么本质区别？防御侧重点是否相同？",
        "reference": "反射型依赖诱导受害者点击构造链接，payload 不落库、影响单次请求；存储型 payload 写入服务端并对所有访问者生效，危害更大。两者防御都靠输出编码，但存储型还需在入库和展示两端都处理。",
        "explanation": "区别在于 payload 是否持久化，这决定了受影响范围和排查方式。",
        "correct": [
            "反射型要骗用户点特制链接，payload 不存服务器，只影响这一次请求；存储型写进数据库，之后所有看到这条内容的人都会中招，危害大得多。防御都要输出编码，存储型还得注意入库和展示两端。",
            "本质区别是 payload 存不存。存储型进了数据库会持续影响所有访问者，反射型只在被诱导点击的那一次生效。修复都靠按上下文编码。",
            "存储型是持久化的，一次注入长期生效、影响面是全体用户；反射型需要社工诱导且一次性。两者都要输出编码，存储型还要清理已入库的脏数据。",
        ],
        "wrong": [
            "存储型比反射型危险，其他没什么区别。",
            "反射型是前端的问题，存储型是后端的问题。",
            "存储型要过滤输入，反射型要过滤输出。",
            "只写出了名词解释，没说触发方式和危害范围。",
        ],
    },
    {
        "id": 301, "module": 3, "task": 1, "difficulty": "medium",
        "desired_rate": 0.28,
        "title": "CSRF Token 会话绑定",
        "stem": "CSRF Token 为什么需要与用户会话绑定并由服务端校验？",
        "reference": "Token 必须与会话绑定并在服务端逐次比对，只在页面放置随机值而不做服务端校验不能形成防护。",
        "explanation": "只在页面放置随机值但不做服务端校验不能形成防护。",
        "correct": [
            "如果不和会话绑定，攻击者自己拿一个合法 token 就能给别人用。必须服务端存一份和当前 session 对应的值，每次提交都比对。",
            "Token 的作用是证明请求来自本站页面。不绑定会话就无法区分是哪个用户的 token，服务端不校验等于没做。",
            "服务端要把 token 和 session 关联存储，收到请求时取出来比对，不一致就拒绝，否则伪造请求照样能通过。",
        ],
        "wrong": [
            "页面里放一个随机 token 就能防住 CSRF 了。",
            "校验 Referer 头就够了，不需要 token。",
            "只写出了部分步骤，缺少验证依据。",
        ],
    },
    {
        "id": 302, "module": 3, "task": 2, "difficulty": "easy",
        "desired_rate": 0.13,
        "title": "SameSite Cookie 与 CSRF 防御",
        "stem": "SameSite=Lax 能防住哪些 CSRF 场景？还有哪些场景防不住？",
        "reference": "SameSite=Lax 会在跨站的 POST、iframe、XHR 等请求中不带 Cookie，可挡住多数经典 CSRF；但跨站顶层 GET 导航仍会带 Cookie，因此对用 GET 实现的状态变更无效，仍需 Token 配合。",
        "explanation": "SameSite 是有效的纵深防御，但不能替代 Token，尤其在 GET 被用于写操作时。",
        "correct": [
            "Lax 模式下跨站的 POST、iframe、Ajax 都不带 Cookie，经典的表单型 CSRF 基本挡住了。但跨站点击链接这种顶层 GET 还是会带 Cookie，所以如果用 GET 改状态就防不住，还得配 Token。",
            "能挡住跨站 POST 和子资源请求。防不住顶层 GET 导航，所以写操作绝对不能用 GET，并且仍要保留 Token 校验。",
            "SameSite=Lax 拦掉了大部分跨站带 Cookie 的场景，但顶层 GET 例外。正确做法是写操作只用 POST，再叠加会话绑定的 Token。",
        ],
        "wrong": [
            "设置了 SameSite 就完全不用管 CSRF 了。",
            "SameSite=Lax 会禁止所有跨站请求携带 Cookie。",
        ],
    },
]

# 新增知识点（平台默认只播种 101/102/201/301/401/402/501/601）
NEW_KNOWLEDGE_POINTS = [
    (202, "存储型与反射型XSS区分", "XSS", "区分 payload 是否持久化及其对危害范围与排查方式的影响。", "medium", 2),
    (203, "XSS防御边界与CSP", "XSS", "理解 HttpOnly、CSP 的防护边界，以及为何不能替代输出编码。", "hard", 2),
    (302, "SameSite Cookie与CSRF防御", "CSRF", "理解 SameSite 各模式的生效范围及其对 CSRF 的防护边界。", "easy", 3),
]

COURSES = [
    {"course_id": 1, "name": "SQL注入攻击", "points": KNOWLEDGE_POINTS},
    {"course_id": 2, "name": "XSS与CSRF攻击", "points": XSS_KNOWLEDGE_POINTS},
]

# 学生能力分层：值越高越容易答对
def build_ability():
    abilities = {}
    for i, uid in enumerate(STUDENTS):
        r = random.random()
        if r < 0.20:
            abilities[uid] = random.uniform(0.75, 0.95)   # 强
        elif r < 0.75:
            abilities[uid] = random.uniform(0.45, 0.75)   # 中
        else:
            abilities[uid] = random.uniform(0.15, 0.45)   # 弱
    return abilities

ABILITY = build_ability()


def calibrate(n: int, desired_rate: float) -> tuple[int, int]:
    """反解「最终答错人数 W」与「先错后改对人数 S」，命中后端的错题率口径。

    后端错题率 = 错误作答数 / 全部作答数（含重做），因此：
        错误作答数 = W + round(0.4*W) + S      # 最终错的 + 其中重做仍错的 + 首答失手的
        全部作答数 = n + round(0.4*W) + S
    在所有组合里取最接近目标值的一组，并保证 S>=1 以产生真实重做轨迹。
    """
    best = None
    for W in range(n + 1):
        retry_wrong = round(0.4 * W)
        for S in range(n - W + 1):
            total = n + retry_wrong + S
            if total == 0:
                continue
            rate = (W + retry_wrong + S) / total
            penalty = 0.0 if 1 <= S <= max(1, (n - W) // 3) else 0.03
            score = abs(rate - desired_rate) + penalty
            if best is None or score < best[0]:
                best = (score, W, S)
    return best[1], best[2]

BASE_DATE = datetime(2026, 7, 18, 9, 0, 0)

rows_ts, rows_gq, rows_qkp, rows_att, rows_ev = [], [], [], [], []
q_seq = 0
att_seq = 0
ts_seq = 0

def esc(s):
    return str(s).replace("\\", "\\\\").replace("'", "''")

def jstr(v):
    return esc(json.dumps(v, ensure_ascii=False))

for course in COURSES:
    COURSE_ID = course["course_id"]
    for kp in course["points"]:
        # 每个知识点选一部分学生练习（不是所有人都练所有点）
        participation = random.uniform(0.55, 0.85)
        participants = [u for u in STUDENTS if random.random() < participation]
        if len(participants) < 6:
          participants = random.sample(STUDENTS, 8)

        # 按配额精确控制「最终错题率」（教师端饼图取每题最后一次作答）。
        # 弱势学生优先落在错误名单里，再加少量噪声避免过于规整。
        ranked = sorted(participants, key=lambda u: ABILITY[u] + random.uniform(-0.12, 0.12))
        n_wrong, n_stumble = calibrate(len(ranked), kp["desired_rate"])
        final_wrong = set(ranked[:n_wrong])                       # 能力最弱的一批最终答错
        stumblers = set(ranked[n_wrong:n_wrong + n_stumble])      # 其次的一批先错后改对
        # 最终答错的人里，固定比例会重做一次但仍然没做对
        retry_still_wrong = set(ranked[:round(0.4 * n_wrong)])

        for uid in participants:
            ts_seq += 1
            q_seq += 1
            sid = f"{PREFIX}-ts-{ts_seq:04d}"
            qid = f"{PREFIX}-q-{q_seq:04d}"
            numeric = NUMERIC_BASE + q_seq

            day_offset = random.randint(0, 18)
            hour = random.randint(9, 21)
            created = BASE_DATE + timedelta(days=day_offset, hours=hour - 9,
                                            minutes=random.randint(0, 59))

            rows_ts.append(
                f"('{sid}', {uid}, {ADMIN_CLASS_ID}, {COURSE_ID}, 'personalized_training', "
                f"'{jstr({'weakKnowledgePoints': [kp['id']]})}', "
                f"'{jstr({'source': 'student_profile', 'teachingClassId': TEACHING_CLASS_ID})}', "
                f"'{created:%Y-%m-%d %H:%M:%S}')"
            )
            raw_ai = {"generationReason": f"根据画像薄弱点 {kp['title']} 生成"}
            rows_gq.append(
                f"('{qid}', {numeric}, '{sid}', 'short_answer', {kp['id']}, {kp['module']}, {kp['task']}, "
                f"'{kp['difficulty']}', '{esc(kp['title'])}', '{esc(kp['stem'])}', "
                f"'{esc(kp['reference'])}', '{esc(kp['explanation'])}', 'deepseek-chat', "
                f"'{jstr(raw_ai)}', "
                f"'{created:%Y-%m-%d %H:%M:%S}')"
            )
            rows_qkp.append(f"({numeric}, '{qid}', '{qid}', {kp['id']}, 1.00)")

            # 最终答错的必然首答错；最终答对的里也有一部分是「先错后改对」，
            # 这样才有真实的重做轨迹和能力成长证据。
            ends_wrong = uid in final_wrong
            first_wrong = ends_wrong or (uid in stumblers)

            submitted = created + timedelta(minutes=random.randint(3, 40))
            att_seq += 1
            if first_wrong:
                ans = random.choice(kp["wrong"])
                score = round(random.uniform(38, 68), 2)
                correct = 0
            else:
                ans = random.choice(kp["correct"])
                score = round(random.uniform(84, 99), 2)
                correct = 1
            cost = random.randint(45, 320) if first_wrong else random.randint(30, 210)

            rows_att.append(
                f"('{PREFIX}-att-{att_seq:04d}', '{sid}', '{qid}', {uid}, '{jstr(ans)}', "
                f"{correct}, {score}, {cost}, '{submitted:%Y-%m-%d %H:%M:%S}')"
            )
            rows_ev.append(
                f"('{PREFIX}-evt-{att_seq:04d}', {uid}, {ADMIN_CLASS_ID}, {COURSE_ID}, {kp['module']}, {kp['task']}, "
                f"'QUESTION_SUBMIT', '{submitted:%Y-%m-%d %H:%M:%S}', "
                f"'{jstr({'score': score, 'answer': ans, 'isCorrect': bool(correct), 'knowledgePointId': kp['id'], 'generatedQuestionId': qid})}', "
                f"'{SOURCE}', '{PREFIX}-req-{att_seq:04d}')"
            )

            # 重做规则必须和「最终对错」自洽：
            #   首答错但最终算对 -> 一定有一次改对的重做（成长证据）
            #   最终仍算错       -> 可能重做过，但仍然没做对
            if first_wrong and not ends_wrong:
                do_retry, improved = True, True          # 先错后改对：必然有第二次作答
            elif first_wrong:
                do_retry, improved = (uid in retry_still_wrong), False
            else:
                do_retry, improved = False, False

            if do_retry:
                att_seq += 1
                retry_at = submitted + timedelta(days=random.randint(1, 4),
                                                 minutes=random.randint(5, 300))
                if improved:
                    ans2 = random.choice(kp["correct"])
                    score2 = round(random.uniform(80, 96), 2)
                    correct2 = 1
                else:
                    ans2 = random.choice(kp["wrong"])
                    score2 = round(random.uniform(45, 70), 2)
                    correct2 = 0
                cost2 = random.randint(40, 240)
                rows_att.append(
                    f"('{PREFIX}-att-{att_seq:04d}', '{sid}', '{qid}', {uid}, '{jstr(ans2)}', "
                    f"{correct2}, {score2}, {cost2}, '{retry_at:%Y-%m-%d %H:%M:%S}')"
                )
                rows_ev.append(
                    f"('{PREFIX}-evt-{att_seq:04d}', {uid}, {ADMIN_CLASS_ID}, {COURSE_ID}, {kp['module']}, {kp['task']}, "
                    f"'QUESTION_SUBMIT', '{retry_at:%Y-%m-%d %H:%M:%S}', "
                    f"'{jstr({'score': score2, 'answer': ans2, 'isCorrect': bool(correct2), 'knowledgePointId': kp['id'], 'generatedQuestionId': qid, 'retry': True})}', "
                    f"'{SOURCE}', '{PREFIX}-req-{att_seq:04d}')"
                )


def block(header, cols, rows):
    out = [f"INSERT INTO {header} ({cols}) VALUES"]
    out.append(",\n".join("  " + r for r in rows) + ";")
    return "\n".join(out)


NEW_KP_VALUES = ",\n".join(
    f"  ({kid}, '{esc(name)}', '{esc(cat)}', '{esc(desc)}', '{esc(diff)}', 1)"
    for kid, name, cat, desc, diff, _mod in NEW_KNOWLEDGE_POINTS
) + ";"
NEW_KP_VALUES = NEW_KP_VALUES.rstrip(";")

NEW_MODULE_KP_VALUES = ",\n".join(
    f"  ({mod}, {kid}, 1.00)" for kid, _n, _c, _d, _diff, mod in NEW_KNOWLEDGE_POINTS
)

sql = f"""-- 网安242班 模拟学习数据（教师端验证用）
-- 由 scripts 生成，随机种子 20260808，结果可复现。
--
-- 用途：让教师端「教学分析」在 242 班上有完整可验证的数据
--       （知识点错误分布饼图、知识点详情、AI 分析、学生画像）。
--
-- 【重要】这是模拟数据，不是真实学生操作产生的记录。
--   - 所有主键以 '{PREFIX}-' 开头，可整体清除，不影响其它数据
--   - learning_event.source 写成 '{SOURCE}'（生产来源），
--     因此画像与能力成长会把它当作真实证据纳入统计。
--     如果你希望它被画像排除，把 source 改成 'showcase-seed' 再执行。
--
-- 覆盖课程：{" / ".join(f"{c['name']}(course_id={c['course_id']}, {len(c['points'])}个知识点)" for c in COURSES)}
--
-- 数据规模：
--   训练会话 {len(rows_ts)} 个
--   生成题 {len(rows_gq)} 道 | 作答记录 {len(rows_att)} 条（含重做）
--   学生 {len(STUDENTS)} 人（教学班 {TEACHING_CLASS_ID} / 行政班 {ADMIN_CLASS_ID}）
--   时间跨度 2026-07-18 ~ 2026-08-05
--
-- 可重复执行：每次先删除 '{PREFIX}-' 前缀数据再重新写入。

START TRANSACTION;

-- 前置条件：教师端「教学分析」的知识点风险查询里有
--   INNER JOIN teaching_class_course ON teaching_class_id AND course_id
-- 教学班没安排课程时，即使学生作答数据齐全，饼图也会是空的。
-- 242 班原本一门课都没关联，这里补上与 232 班一致的三门。
INSERT INTO `{USER_SCHEMA}`.`teaching_class_course`
  (`teaching_class_id`, `course_id`, `teaching_order`, `planned_start_date`, `planned_end_date`, `created_at`, `updated_at`)
SELECT * FROM (
  SELECT {TEACHING_CLASS_ID} AS a, 1 AS b, 1 AS c, '2026-07-18' AS d, '2026-08-15' AS e, NOW(6) AS f, NOW(6) AS g
  UNION ALL SELECT {TEACHING_CLASS_ID}, 2, 2, '2026-08-16', '2026-09-10', NOW(6), NOW(6)
  UNION ALL SELECT {TEACHING_CLASS_ID}, 3, 3, '2026-09-11', '2026-10-08', NOW(6), NOW(6)
) AS src
WHERE NOT EXISTS (
  SELECT 1 FROM `{USER_SCHEMA}`.`teaching_class_course` t
  WHERE t.`teaching_class_id` = src.a AND t.`course_id` = src.b
);

-- XSS/CSRF 课程专属知识点：平台默认只播种 8 个（101/102/201/301/401/402/501/601），
-- 其中属于本课程的只有 201 和 301，饼图只有两块太单薄，这里补齐到 5 个。
-- 用 ON DUPLICATE KEY UPDATE 保证可重复执行，也不会被应用启动时的默认播种覆盖。
INSERT INTO `seclab_profile`.`knowledge_point`
  (`knowledge_point_id`, `name`, `category`, `description`, `difficulty_level`, `is_active`)
VALUES
{NEW_KP_VALUES}
ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `category`=VALUES(`category`),
  `description`=VALUES(`description`), `difficulty_level`=VALUES(`difficulty_level`);

INSERT INTO `seclab_profile`.`module_knowledge_point` (`module_id`, `knowledge_point_id`, `relevance_weight`)
VALUES
{NEW_MODULE_KP_VALUES}
ON DUPLICATE KEY UPDATE `relevance_weight`=VALUES(`relevance_weight`);

DELETE FROM `seclab_profile`.`learning_event`              WHERE `event_id` LIKE '{PREFIX}-%';
DELETE FROM `seclab_profile`.`generated_question_attempt`  WHERE `attempt_id` LIKE '{PREFIX}-%';
DELETE FROM `seclab_profile`.`question_knowledge_point`    WHERE `generated_question_id` LIKE '{PREFIX}-%';
DELETE FROM `seclab_profile`.`generated_question`          WHERE `generated_question_id` LIKE '{PREFIX}-%';
DELETE FROM `seclab_profile`.`training_session`            WHERE `training_session_id` LIKE '{PREFIX}-%';

{block("`seclab_profile`.`training_session`",
       "`training_session_id`, `user_id`, `class_id`, `course_id`, `source_type`, `diagnose_result_json`, `training_context_json`, `created_at`",
       rows_ts)}

{block("`seclab_profile`.`generated_question`",
       "`generated_question_id`, `question_numeric_id`, `training_session_id`, `question_type`, `knowledge_point_id`, `module_id`, `task_id`, `difficulty`, `title`, `stem`, `reference_answer`, `explanation`, `source_model`, `raw_ai_json`, `created_at`",
       rows_gq)}

{block("`seclab_profile`.`question_knowledge_point`",
       "`question_id`, `question_uid`, `generated_question_id`, `knowledge_point_id`, `relevance_weight`",
       rows_qkp)}

{block("`seclab_profile`.`generated_question_attempt`",
       "`attempt_id`, `training_session_id`, `generated_question_id`, `user_id`, `answer_json`, `is_correct`, `score`, `cost_time`, `submitted_at`",
       rows_att)}

{block("`seclab_profile`.`learning_event`",
       "`event_id`, `user_id`, `class_id`, `course_id`, `module_id`, `task_id`, `event_type`, `event_time`, `payload_json`, `source`, `request_id`",
       rows_ev)}

COMMIT;
"""

path = r"d:/Seclab/SecLab-Combined/database/sql/seed_class242_simulation.sql"
with open(path, "w", encoding="utf-8") as f:
    f.write(sql)

# 打印预期分布，便于核对
print(f"生成完成: {path}")
print(f"  训练会话 {len(rows_ts)} | 生成题 {len(rows_gq)} | 作答 {len(rows_att)} | 事件 {len(rows_ev)}")
print("\n各知识点预期表现（按首次作答口径估算）:")
