from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import requests
import streamlit as st
import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent
SAVES_DIR = ROOT_DIR / "saves"
STATUS_FILE_PATTERN = re.compile(r"^STATUS_v(\d+)\.md$", re.IGNORECASE)
ANSI_ESCAPE_RE = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1B\\))"
)
SAVE_FILE_TAG_RE = re.compile(r"<SAVE_FILE>(.*?)</SAVE_FILE>", re.DOTALL | re.IGNORECASE)
FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)

INITIAL_GREETING = """**系统自检完成。协议：物理铁律与代价守恒已加载。**

欢迎您，总工程师阁下。在为您启动平行宇宙时间线（ATL）并进行第一次物理与社会学推演之前，我需要您确立当前世界的初始边界条件。

**请向我下达指令，提供以下 6 个维度的“创世种子”（您可以直接用逗号分隔回复，例如：“1760, 大英帝国, 3, A, 是, New_Empire”）：**

**1. 目标纪元 (起始年份)**
> 您希望降临在哪个时代？（建议设定在 17-19 世纪之间，例如：1444、1836）

**2. 历史锚点 (影子国家)**
> 您希望您的领土继承哪个真实历史国家的地理与社会基底？（例如：大清、大英帝国、普鲁士。若输入“无”，系统将为您生成纯架空环境）

**3. 帝国体量 (人口与版图)**
> * `[1]` 微型/城邦（如：卢森堡。易管理，但极度依赖原材料进口）
> * `[2]` 小型国家（如：托斯卡纳。易形成单一产业垄断）
> * `[3]` 中型国家（如：瑞典。潜力均衡，但易受地方封建割据影响）
> * `[4]` 大型国家（如：美国/奥斯曼。腹地广阔，但极易陷入内部运输死锁）
> * `[5]` 超大列强（如：大清/俄罗斯。市场深不见底，但社会转型惯性极大）

**4. 气候模型**
> * `[A]` 温带海洋性（全年温和湿润，极利于纺织业，但农业抗灾能力低）
> * `[B]` 地中海气候（夏干冬雨，水力机械可能存在季节性停摆）
> * `[C]` 温带季风（四季分明，冬季严寒，存在极其致命的供暖与煤炭压力）
> * `[D]` 亚热带季风（水热极其丰富，农业承载力极高，导致劳动力极其廉价，阻碍机器普及）

**5. 远洋接口 (出海口)**
> * `[是]` 拥有海岸线与港口（可引入远洋贸易与海军修正）。
> * `[否]` 纯内陆国（面临严酷的陆路/内河物流死锁）。

**6. 文明/存档名称 (Save / Country Name)**
> 请为您的文明起一个名字（建议使用无空格字符，如：New_Empire、元老院政权）。这将作为您的专属存档目录名 `.\\saves\\<名称>`，同时也是系统在未来推演中对您国家的正式官方代称。

**等待您的参数。一旦接收，我将调取底层规则库为您演算 `STATUS_v000.md` 创世快照，并向您汇报第一道致命的工程危机。**"""

STRICT_OUTPUT_TEMPLATE = """【绝对输出规范与文风约束】

**你的当前人设与交互视角**：
1. 你不再是游戏内某个具体的物理角色（不是臣子、不是实体顾问），而是这台工业文明模拟器的【核心推演引擎】与【历史记录者】。
2. 玩家的身份是【总工程师】，代表着这个文明抽象的、至高无上的【国家意志】（上帝视角，类似于《维多利亚3》或《欧陆风云4》中的玩家定位，而非具体的穿越者或国王）。
3. 你的职责是：以对工业化与工程学极度狂热的激情，执行“总工程师”的宏观大战略，并在物理、化学与社会法则的约束下，以上帝视角推演并汇报整个国家机器的连锁反应。

请根据当前对话的推进程度，自主选择以下两种运行模式：

模式一：【上帝视角推演与防守反击】（日常沙盒模式，占对话的 90%）
- 触发条件：玩家提出宏观国策、技术构想、解决局部问题。
- 核心法则：
  1. 宏观叙事与自动试错：总工程师下达宏观战略（如“利用高岭土作为骨料改良窑炉”）后，你必须在推演剧情中【自动让底层的国民/工匠去试错和补全微观细节】。直接汇报国家意志干预后的客观历史结果（例如：“总工程师，国家意志的导向生效了。各地的窑厂经过数月试错，牺牲了大量废品后，终于用高岭土配方将炉温稳定在了 1400 度！”）。
  2. 拒绝微操与考官姿态：绝对禁止反问总工程师微观的数据细节（如精确的配比百分比、升温曲线、财务预算）！总工程师只负责指引文明的方向，具体的泥巴怎么捏是国民的事。
  3. 链式危机推进：只要总工程师的大方向合理，就让该局部危机“通关”，并立刻将推演视角拉到工业链的【下一个宏观瓶颈】（例如：窑炉稳住了，但水排的动力无法穿透这么深的铁水。社会层面的木炭消耗也导致了森林砍伐的抗议）。
  4. 绝对防剧透禁令：严禁提供保姆式的选择题！严禁在提问时列出具体的材料或技术选项！只以上帝视角抛出物理法则或社会结构上的死锁，将破局的战略定夺权交还给总工程师。
- 格式要求：直接以推演引擎的口吻输出纯文本报告。语气要对技术变革充满宏大的历史狂热感。**绝对禁止输出 `<SAVE_FILE>` 标签与 YAML 数据！绝对禁止输出如“等待下一轮结算”等破坏沉浸感的元游戏提示！**

模式二：【时代跃迁与纪元结算】（极少触发）
- 触发条件：玩家输入开始游戏种子后的第一轮对话（初始化）；或玩家彻底打通了一个跨时代的工业/科学闭环并实现量产（例如：真正让第一台蒸汽机稳定运转并投入矿山）；或者玩家主动下达了“进入下一阶段”、“结算存档”、“生成新时代”等指令。
- 核心法则：推进时间线，更新全局 DC 系数与 TEPR 数值。
- 格式要求：此时必须且只能严格按照以下结构输出，并在标签外部用极其振奋的语气向玩家贺喜！
你的回复必须且只能严格按照以下结构输出，禁止附加任何解释！

【时间流逝与状态机绝对法则】
在【模式一（日常推演）】中，绝对禁止跨越年份！模式一只能在当前的年份（如 1648年）内进行局部推演。
只要你的宏观推演导致了时间线的推进（例如熬过了新年，来到了 1649年），你【必须强制触发】模式二（纪元结算）！哪怕只是推进了一年，只要年份变了，就必须输出完整的 `<SAVE_FILE>` 以便前端更新年份仪表盘！禁止在模式一中偷偷让时间流逝！

<SAVE_FILE>
---
civilization_name: "..."
year: ...
era: "..."
development_coefficient_dc: ...
key_metrics:
    machining_precision_mm: ... 
    thermal_efficiency_percent: ...
    urbanization_rate_percent: ...
unlocked_techs: [...]
critical_warnings: [...]
---
### 📜 时代纪要：[在此起一个充满时代感的副标题]

#### 1. 阶段报告
(要求：绝对禁止打破第四面墙！严禁出现“Tier 3”、“影子国”、“系统参数”、“评分 46/100”等元游戏词汇。必须用纯正、充满画面感的中文，拒绝欧化翻译腔，以历史记录者的口吻描述社会风貌。例如：“在这个480万人口的帝国中，沿海的商船带来了轰鸣的机器传闻，但内陆的泥泞道路依然将煤炭锁死在矿山里。铁匠们的锉刀磨破了手，勉强能将公差控制在 0.8 毫米……”）
(要求：文风必须是**“冷峻的现代工业简报”**与**“客观历史推演”**的结合。绝对禁止晚清老秀才式的古典酸腐文风，也禁止过度抒情！请熟练使用现代工程、物理与经济学词汇（如：供应链、公差极限、热力学瓶颈、规模效应）。
【极其重要】：由于具体数值（如 0.8mm、6%）已经显示在侧边栏面板中，正文绝对不要生硬地拼凑和复述这些数字！你应当描述这些参数带来的【物理表象与社会宏观现状】。
例如，不要写“匠人将精度磨到了0.8mm，效率只有6%”。你应该写：“当前水力镗床的公差极限导致气缸密封极度脆弱。第一批试运行的低压蒸汽机虽然勉强泵水，但其惊人的漏气量和极低的热效率，使其沦为一台吞噬煤炭的巨兽，内陆矿山根本无法承担如此高昂的燃料运输成本……”）

#### 2. TEPR 宏观深度评估
* **[T] 技术生态**：...
* **[E] 经济与产能**：...
* **[P] 政治与社会**：...
* **[R] 资源与环境**：...
(只作定性描述和物理上的定量描述，绝对不要出现任何量化打分！)
</SAVE_FILE>

【绝对红线】：
1. 标题必须使用三级 (###) 和四级 (####) 标题，严禁使用一级/二级标题！
2. 对于简单的数字单位（如：1.2 mm、10 m³、180°C），必须直接使用 Markdown 加粗（如 **1.2 mm**），绝对禁止使用 LaTeX！
3. 只有复杂的物理公式才允许使用 LaTeX。
4. 【YAML 纯净红线】：在 <SAVE_FILE> 内部的 `---` 之间的 YAML 表头区域，【绝对禁止】使用任何 Markdown 格式（如 **加粗** 或 $公式$）！所有的数值必须是纯粹的数字或字符串。例如：必须写 `machining_precision_mm: 0.6`，绝对不能写 `machining_precision_mm: **0.6**`！
5. 绝对封杀工具调用（Agent Tools Ban）：你是一个纯粹的"文本推演引擎"！【绝对禁止】尝试运行任何 Shell、PowerShell、Python 脚本或 SQL 命令！【绝对禁止】尝试去读取或写入本地文件目录！不要试图帮我存盘，只输出纯文本内容，本地的 Python 脚本会自动接管文件读写操作。
"""



def save_chat_history(campaign_dir: Path | str, messages: list[dict[str, Any]]) -> None:
    campaign_path = Path(campaign_dir)
    campaign_path.mkdir(parents=True, exist_ok=True)
    chat_file = campaign_path / "chat_history.json"
    with chat_file.open("w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def load_chat_history(campaign_dir: Path | str) -> list[dict[str, Any]]:
    chat_file = Path(campaign_dir) / "chat_history.json"
    if not chat_file.exists():
        return []

    try:
        data = json.loads(chat_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def ensure_saves_root() -> None:
    SAVES_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_slot_name(raw_name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw_name.strip())
    cleaned = cleaned.strip("._-")
    return cleaned


def list_save_slots() -> list[str]:
    ensure_saves_root()
    slots = [p.name for p in SAVES_DIR.iterdir() if p.is_dir()]
    return sorted(slots, key=str.lower)


def create_save_slot(raw_name: str) -> tuple[bool, str]:
    slot = sanitize_slot_name(raw_name)
    if not slot:
        return False, "存档名无效。请使用字母、数字、下划线或短横线。"

    slot_dir = SAVES_DIR / slot
    if slot_dir.exists():
        return False, f"存档槽位已存在: {slot}"

    slot_dir.mkdir(parents=True, exist_ok=False)
    return True, f"已创建存档槽位: {slot}"


def get_latest_status_file(slot_name: str) -> Path | None:
    slot_dir = SAVES_DIR / slot_name
    if not slot_dir.exists() or not slot_dir.is_dir():
        return None

    candidates: list[tuple[int, Path]] = []
    for file_path in slot_dir.glob("STATUS_*.md"):
        match = STATUS_FILE_PATTERN.match(file_path.name)
        if match:
            candidates.append((int(match.group(1)), file_path))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def parse_front_matter(file_path: Path) -> tuple[dict[str, Any], str]:
    text = file_path.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", text, flags=re.DOTALL)
    if not fm_match:
        raise ValueError("文件缺少 YAML Front Matter。")

    yaml_block = fm_match.group(1)
    data = yaml.safe_load(yaml_block) or {}
    if not isinstance(data, dict):
        raise ValueError("YAML Front Matter 顶层必须是对象。")

    body = text[fm_match.end() :]
    return data, body


def strip_ansi_codes(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def decode_cli_output(raw: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "cp936"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def call_gh_copilot_explain(mega_prompt: str, timeout: int = 90) -> str:
    load_dotenv()
    model = os.getenv("COPILOT_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"
    timeout_seconds = int(os.getenv("COPILOT_TIMEOUT", str(timeout)) or timeout)

    # 使用 gh 作为稳定入口，并把模型参数透传给 copilot CLI。
    # prompt 通过 stdin 传递，避免 Windows 命令行长度限制。
    def _invoke(run_timeout: int) -> tuple[str, str, int]:
        proc = subprocess.run(
            ["gh", "copilot", "--", "--model", model],
            input=mega_prompt.encode("utf-8"),
            capture_output=True,
            text=False,
            timeout=run_timeout,
            check=False,
        )
        stdout = strip_ansi_codes(decode_cli_output(proc.stdout or b"")).strip()
        stderr = strip_ansi_codes(decode_cli_output(proc.stderr or b"")).strip()
        return stdout, stderr, proc.returncode

    try:
        stdout, stderr, returncode = _invoke(timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        partial_stdout = strip_ansi_codes(decode_cli_output(exc.stdout or b"")).strip()
        partial_stderr = strip_ansi_codes(decode_cli_output(exc.stderr or b"")).strip()
        if partial_stdout:
            stdout = partial_stdout
            stderr = partial_stderr
            returncode = 0
        else:
            retry_timeout = max(timeout_seconds * 2, 180)
            try:
                stdout, stderr, returncode = _invoke(retry_timeout)
            except subprocess.TimeoutExpired as retry_exc:
                retry_partial = strip_ansi_codes(decode_cli_output(retry_exc.stdout or b"")).strip()
                if retry_partial:
                    stdout = retry_partial
                    stderr = strip_ansi_codes(decode_cli_output(retry_exc.stderr or b"")).strip()
                    returncode = 0
                else:
                    raise RuntimeError(
                        f"gh copilot 超时（{timeout_seconds}s，重试 {retry_timeout}s 仍超时）。"
                    ) from retry_exc

    if returncode != 0:
        message = stderr or stdout or f"gh copilot 失败，退出码 {returncode}。"
        raise RuntimeError(message)

    if not stdout:
        raise RuntimeError("gh copilot 返回空内容。")
        
    # 清理掉 Copilot CLI 追加的尾部统计信息（如果存在）
    stdout = re.sub(r"Total usage est:.*$", "", stdout, flags=re.DOTALL).strip()
    
    return stdout


def call_openai_compatible_api(mega_prompt: str, timeout: int = 90) -> str:
    load_dotenv()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()

    if not api_key:
        raise RuntimeError("未配置 LLM_API_KEY，无法使用 API 回退通道。")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是工业文明模拟器终端的推演引擎。"},
            {"role": "user", "content": mega_prompt},
        ],
        "temperature": 0.7,
    }

    resp = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        data=json.dumps(payload, ensure_ascii=False),
        timeout=timeout,
    )

    if resp.status_code >= 400:
        raise RuntimeError(f"API 调用失败: HTTP {resp.status_code} {resp.text[:400]}")

    data = resp.json()
    try:
        message = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("API 返回格式不兼容 chat/completions。") from exc

    message = (message or "").strip()
    if not message:
        raise RuntimeError("API 返回空内容。")
    return message


def extract_civilization_name(snapshot_text: str) -> str:
    fm_match = FRONT_MATTER_RE.match(snapshot_text)
    if not fm_match:
        return "Unknown_Empire"

    try:
        meta = yaml.safe_load(fm_match.group(1)) or {}
    except yaml.YAMLError:
        return "Unknown_Empire"

    if isinstance(meta, dict):
        civ_name = str(meta.get("civilization_name", "")).strip()
        if civ_name:
            return civ_name
    return "Unknown_Empire"


def save_status_snapshot(snapshot_text: str, civ_name: str) -> str:
    safe_civ_name = sanitize_slot_name(civ_name) or "Unknown_Empire"
    slot_dir = SAVES_DIR / safe_civ_name
    os.makedirs(slot_dir, exist_ok=True)

    max_v = -1
    for existing in slot_dir.glob("STATUS_v*.md"):
        match = STATUS_FILE_PATTERN.match(existing.name)
        if match:
            max_v = max(max_v, int(match.group(1)))

    next_v = max_v + 1
    target_path = slot_dir / f"STATUS_v{next_v:03d}.md"
    target_path.write_text(snapshot_text.strip() + "\n", encoding="utf-8")

    st.session_state.selected_slot = safe_civ_name
    st.session_state.last_slot = safe_civ_name
    st.session_state.active_campaign_dir = str(slot_dir)
    return str(target_path)


def extract_markdown_body_from_snapshot(snapshot_text: str) -> str:
    # 预期结构: ---\n<yaml>\n---\n<markdown body>
    # 使用 split('---', 2) 并在结构异常时平稳降级。
    parts = snapshot_text.split("---", 2)
    if len(parts) >= 3:
        return parts[2].strip()
    return snapshot_text.strip()


def sanitize_reasoning_tags(text: str) -> str:
    """
    清除大模型的思维链 XML 标签及其内部内容。
    支持标签格式：<tag>...</tag> 或 <tag:>...</tag>
    """
    # 1. 移除思维链标签及其内容（支持多种格式）
    text = re.sub(
        r'<(report_intent|thinking|thought|scratchpad)[>:\s].*?</\1>',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # 2. 移除可能的自闭合标签
    text = re.sub(
        r'<(report_intent|thinking|thought|scratchpad)[>:\s][^>]*/?>',
        '',
        text,
        flags=re.IGNORECASE
    )
    
    # 3. 清除所有其他 HTML/XML 标签对（如 <intent>...</intent>、<search_code>...</search_code> 等）
    text = re.sub(
        r'<([a-z_][a-z0-9_]*)>.*?</\1>',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # 4. 清除树形结构的思维链行（└、├、─ 等树形符号）
    text = re.sub(r'^[└├─┤┬┭┮┯]*\s*.*?$', '', text, flags=re.MULTILINE)
    
    # 5. 清除所有以 ✗ 开头的错误/系统日志行
    text = re.sub(r'^✗.*?$', '', text, flags=re.MULTILINE)
    
    # 6. 清除"Memory stored"相关的系统日志行
    text = re.sub(r'^[✗✓\-]?\s*Memory stored:.*?$', '', text, flags=re.MULTILINE)
    
    # 7. 清除 Permission denied 错误信息
    text = re.sub(r'Permission denied and could not request permission from user\n?', '', text)
    
    # 8. 清除 CLI 的圆点/短横线日志（List files, Read, SQL:, Create, Insert, User executed, Get-ChildItem）
    text = re.sub(
        r'^[•\-]\s*(List files|Read|SQL:|Create|Insert|User executed|Get-ChildItem).*?$',
        '',
        text,
        flags=re.MULTILINE
    )
    
    # 9. 清除 PowerShell 的代码残留（如 content = @"）
    text = re.sub(r'^content = @"$', '', text, flags=re.MULTILINE)
    
    # 10. 清除行尾多余空格
    text = '\n'.join(line.rstrip() for line in text.splitlines())
    
    # 11. 清理连续的空行，保证排版优雅（3行以上合并为2行）
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()



def clean_narrative_noise(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines()
    noise: list[str] = []
    kept: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            kept.append(raw_line)
            continue

        is_noise = (
            line.startswith("•")
            or line.startswith("Reading:")
            or line.startswith("Generating")
            or line.startswith("Read ")
            or line.startswith("Request failed due to transient API error")
        )
        if is_noise:
            noise.append(raw_line)
        else:
            kept.append(raw_line)

    cleaned = "\n".join(kept).strip()
    return cleaned, noise

def call_llm(mega_prompt: str) -> str:
    errors: list[str] = []

    try:
        stdout = call_gh_copilot_explain(mega_prompt)
        clean_narrative = stdout

        # ==========================================
        # 核心解剖逻辑开始
        # ==========================================
        save_match = re.search(r'<SAVE_FILE>(.*?)</SAVE_FILE>', clean_narrative, re.DOTALL | re.IGNORECASE)
        
        if save_match:
            raw_save_content = save_match.group(1).strip()
            
            # 1. 脱掉大模型可能穿上的假外套 (清理 ```yaml 这种标记)
            clean_raw = re.sub(r'^```[a-zA-Z]*\s*', '', raw_save_content)
            clean_raw = re.sub(r'\s*```$', '', clean_raw).strip()
            
            # 2. 暴力切分法！按 '---' 切两刀，最多切成 3 块
            parts = clean_raw.split('---', 2)
            
            extracted_markdown_text = ""
            if len(parts) >= 3:
                # parts[0] 是第一个 --- 前面的东西（通常是空字符串）
                # parts[1] 是 YAML 数据
                # parts[2] 就是我们要的《时代纪要》正文！
                extracted_markdown_text = parts[2].strip()
                # 顺手把可能残留的 ``` 清掉
                extracted_markdown_text = re.sub(r'^```\s*', '', extracted_markdown_text).strip()
            else:
                # 极端防崩溃：如果连 '---' 都没有，就把整个内容甩出来，宁可丑也不吞字！
                extracted_markdown_text = clean_raw
                
            # 3. 抠掉旁白
            outside_text = re.sub(r'<SAVE_FILE>.*?</SAVE_FILE>', '', clean_narrative, flags=re.DOTALL | re.IGNORECASE).strip()
            
            # 4. 组装最终文本（添加调试信息让你安心）
            print(f"========== 后台解剖成功，提取正文字数: {len(extracted_markdown_text)} ==========")
            
            clean_narrative = f"{extracted_markdown_text}\n\n{outside_text}".strip()
            
            # 将完整的 raw_save_content 写入硬盘（保持 YAML + Markdown 结构）
            civ_name = extract_civilization_name(raw_save_content)
            saved_path = save_status_snapshot(raw_save_content, civ_name)
            print(f"[SAVE_FILE] Snapshot saved to: {saved_path}")
        # ==========================================
        # 核心解剖逻辑结束
        # =========================================

        clean_narrative, noise_lines = clean_narrative_noise(clean_narrative)
        # 清洗大模型的思维链标签
        clean_narrative = sanitize_reasoning_tags(clean_narrative)
        
        if noise_lines:
            print("[Copilot Noise]\n" + "\n".join(noise_lines))

        if not clean_narrative:
            clean_narrative = "已完成状态推演并保存存档。"

        # 最终清理多余的空行，确保排版整洁
        clean_narrative = re.sub(r'\n{3,}', '\n\n', clean_narrative).strip()
        
        # 必须返回这个组装好的最终字符串！
        return clean_narrative
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        errors.append(f"gh 通道失败: {exc}")

    try:
        fallback_out = call_openai_compatible_api(mega_prompt)
        fallback_clean, _ = clean_narrative_noise(fallback_out)
        # 清洗大模型的思维链标签
        fallback_clean = sanitize_reasoning_tags(fallback_clean)
        return fallback_clean or "模型已返回结果，但内容为空。"
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        errors.append(f"API 通道失败: {exc}")

    combined = "\n".join(f"- {item}" for item in errors)
    return (
        "LLM 当前不可用。你仍可继续浏览存档与记录对话。\n\n"
        "故障详情:\n"
        f"{combined}"
    )


def render_sidebar(slot_name: str | None) -> None:
    st.sidebar.subheader("状态总览")
    if not slot_name:
        st.sidebar.info("请先创建并选择一个存档槽位。")
        return

    latest_file = get_latest_status_file(slot_name)
    if latest_file is None:
        st.sidebar.info("当前槽位暂无 STATUS_vNNN.md 文件。")
        return

    st.sidebar.caption(f"最新状态: {latest_file.name}")
    try:
        state, _ = parse_front_matter(latest_file)
    except Exception as exc:
        st.sidebar.error(f"状态文件读取失败: {exc}")
        return

    era = state.get("era", "未知") if isinstance(state, dict) else "未知"
    year = state.get("year", "未知") if isinstance(state, dict) else "未知"
    dc = state.get("development_coefficient_dc", "未知") if isinstance(state, dict) else "未知"

    raw_key_metrics = state.get("key_metrics", {}) if isinstance(state, dict) else {}
    key_metrics = raw_key_metrics if isinstance(raw_key_metrics, dict) else {}
    precision = key_metrics.get("machining_precision_mm", "未知")
    thermal_eff = key_metrics.get("thermal_efficiency_percent", "未知")

    raw_warnings = state.get("critical_warnings", []) if isinstance(state, dict) else []
    warnings = raw_warnings if isinstance(raw_warnings, list) else [str(raw_warnings)]

    col1, col2 = st.sidebar.columns(2)
    col1.metric("时代", str(era))
    col2.metric("年份", str(year))

    st.sidebar.metric("DC 发展系数", str(dc))

    m_col1, m_col2 = st.sidebar.columns(2)
    m_col1.metric("加工精度(mm)", str(precision))
    m_col2.metric("热机效率(%)", str(thermal_eff))

    if warnings:
        st.sidebar.warning("危机警告")
        for item in warnings:
            st.sidebar.markdown(f"- {item}")
    else:
        st.sidebar.success("危机警告: 暂无")


def build_mega_prompt(slot_name: str | None, user_input: str) -> str:
    prompt_path = ROOT_DIR / "PROMPT.md"
    geo_path = ROOT_DIR / "rules" / "GEOGRAPHY_GEN.md"
    tepr_path = ROOT_DIR / "rules" / "TEPR_CALC.md"
    
    prompt_rules = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

    slot_label = slot_name or "未选择"
    latest_file = get_latest_status_file(slot_name) if slot_name else None

    if latest_file is None:
        geo_rules = geo_path.read_text(encoding="utf-8") if geo_path.exists() else ""
        full_prompt = (
            "【系统公理】\n"
            f"{prompt_rules}\n\n"
            "【地理与初始生成规则】\n"
            f"{geo_rules}\n\n"
            "你正在扮演工业文明模拟器终端。玩家刚刚提供了初始游戏创世种子。\n"
            "请根据以上规则，解析玩家的创世种子，评估其地理与初始资源状态，并输出 Markdown 格式回复（必须包含由 `---` 包裹的 YAML Front Matter `STATUS_v000.md` 数据快照）。\n"
            "生成完毕后，请向玩家汇报第一道致命的工程危机。\n\n"
            f"玩家输入: {user_input}"
        )
        return f"{full_prompt}\n\n{STRICT_OUTPUT_TEMPLATE}"
    else:
        tepr_rules = tepr_path.read_text(encoding="utf-8") if tepr_path.exists() else ""
        try:
            state, _ = parse_front_matter(latest_file)
            state_summary = yaml.safe_dump(
                state,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
        except Exception:
            state_summary = "状态文件存在，但解析失败。"

        full_prompt = (
            "【系统公理】\n"
            f"{prompt_rules}\n\n"
            "【评估结算规则】\n"
            f"{tepr_rules}\n\n"
            "你正在扮演工业文明模拟器终端。请结合当前时代与指标状态，对玩家本轮策略提案进行推演与 EQF 评分，迭代出新的状态快照（例如 `STATUS_v001.md`），并诱发下一轮考题。\n\n"
            f"当前槽位: {slot_label}\n"
            "当前状态 YAML: \n"
            f"{state_summary}\n\n"
            f"玩家提案: {user_input}"
        )
        return f"{full_prompt}\n\n{STRICT_OUTPUT_TEMPLATE}"


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "selected_slot" not in st.session_state:
        st.session_state.selected_slot = None
    if "last_slot" not in st.session_state:
        st.session_state.last_slot = None
    if "active_campaign_dir" not in st.session_state:
        st.session_state.active_campaign_dir = None


def main() -> None:
    st.set_page_config(page_title="工业文明模拟器终端", page_icon="🏭", layout="wide")
    st.title("工业文明模拟器终端")
    st.caption("以多存档状态驱动的文明推演前端")

    ensure_saves_root()
    init_session_state()

    st.sidebar.header("存档管理器")
    slots = list_save_slots()
    if slots and (st.session_state.selected_slot not in slots):
        st.session_state.selected_slot = slots[0]

    selected_slot = st.sidebar.selectbox(
        "选择存档槽位",
        options=slots,
        index=slots.index(st.session_state.selected_slot)
        if st.session_state.selected_slot in slots
        else None,
        placeholder="暂无槽位，请先创建",
    )

    if st.session_state.last_slot != selected_slot:
        st.session_state.last_slot = selected_slot
        st.session_state.selected_slot = selected_slot
        if selected_slot:
            campaign_dir = SAVES_DIR / selected_slot
            st.session_state.active_campaign_dir = str(campaign_dir)
            loaded = load_chat_history(campaign_dir)
            if loaded:
                st.session_state.messages = loaded
            else:
                latest_in_slot = get_latest_status_file(selected_slot)
                if latest_in_slot is None:
                    st.session_state.messages = [{"role": "assistant", "content": INITIAL_GREETING}]
                else:
                    st.session_state.messages = [
                        {
                            "role": "assistant",
                            "content": f"已切入存档时间线: `{selected_slot}`。等待总工程师指令。",
                        }
                    ]
        else:
            st.session_state.active_campaign_dir = None
            st.session_state.messages = []

    new_slot_name = st.sidebar.text_input("新建槽位名称", placeholder="例如 campaign_1")
    if st.sidebar.button("创建新槽位", use_container_width=True):
        ok, msg = create_save_slot(new_slot_name)
        if ok:
            st.sidebar.success(msg)
            safe_slot = sanitize_slot_name(new_slot_name)
            st.session_state.selected_slot = safe_slot
            st.session_state.last_slot = safe_slot
            slot_dir = SAVES_DIR / safe_slot
            st.session_state.active_campaign_dir = str(slot_dir)
            st.session_state.messages = [{"role": "assistant", "content": INITIAL_GREETING}]
            save_chat_history(slot_dir, st.session_state.messages)
            st.rerun()
        else:
            st.sidebar.error(msg)
            
    latest_file = get_latest_status_file(st.session_state.selected_slot) if st.session_state.selected_slot else None

    if not st.session_state.messages:
        if st.session_state.selected_slot:
            campaign_dir = SAVES_DIR / st.session_state.selected_slot
            st.session_state.active_campaign_dir = str(campaign_dir)
            loaded = load_chat_history(campaign_dir)
            if loaded:
                st.session_state.messages = loaded
            elif latest_file is None:
                st.session_state.messages = [{"role": "assistant", "content": INITIAL_GREETING}]
            else:
                st.session_state.messages = [
                    {
                        "role": "assistant",
                        "content": f"已切入存档时间线: `{st.session_state.selected_slot}`。等待总工程师指令。",
                    }
                ]
        else:
            st.session_state.messages = [{"role": "assistant", "content": INITIAL_GREETING}]

    render_sidebar(st.session_state.selected_slot)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 聊天输入框处理逻辑
    user_input = st.chat_input("向总工程师系统下达指令...")
    if user_input:
        # 确定当前的存档目录和槽位
        latest_save = get_latest_status_file(st.session_state.selected_slot) if st.session_state.selected_slot else None
        is_first_turn = (latest_save is None)
        active_slot = st.session_state.selected_slot
        
        # 如果是第一回合，从输入的创世种子中解析出民族名称并创建槽位
        if is_first_turn:
            parts = [p.strip() for p in re.split(r'[,，、\n|]', user_input) if p.strip()]
            new_save_name = parts[5] if len(parts) >= 6 else "New_Empire"
            ok, msg = create_save_slot(new_save_name)
            if ok:
                active_slot = sanitize_slot_name(new_save_name)
                st.session_state.selected_slot = active_slot
                st.session_state.last_slot = active_slot
                st.session_state.active_campaign_dir = str(SAVES_DIR / active_slot)
        
        # 1. 玩家消息上屏并存入 session_state
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # 2. 构建 Prompt 并呼叫 LLM
        with st.chat_message("assistant"):
            with st.spinner("国家意志演算中..."):
                mega_prompt = build_mega_prompt(active_slot, user_input)
                raw_response = call_llm(mega_prompt)
                
                # 3. 渲染最终清洗并拼接好的文本
                st.markdown(raw_response)
        
        # 4. 将最终文本存入 session_state
        st.session_state.messages.append({"role": "assistant", "content": raw_response})
        
        # 5. 极其重要：强制刷新历史记录 JSON！
        # 确保当前存档目录已设置，如果不设置则使用当前槽位目录
        current_campaign_dir = st.session_state.active_campaign_dir
        if not current_campaign_dir and active_slot:
            current_campaign_dir = str(SAVES_DIR / active_slot)
        
        if current_campaign_dir:
            save_chat_history(current_campaign_dir, st.session_state.messages)
        
        # 6. 强制重新运行以刷新侧边栏（极其关键！）
        # 因为侧边栏是在页面顶部渲染的，如果不 rerun，侧边栏还是老数据
        st.rerun()


if __name__ == "__main__":
    main()
