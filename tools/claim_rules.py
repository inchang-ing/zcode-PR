"""Shared conservative claim and not-ready checks for issue bodies and comments."""
import re

# 强版软认领正则(补 2026-10-13 两个漏判实例:
#   optuna#6898 "I would like to implement it as Ra1nhy / I will wait for the preferred scope"
#   sklearn#35139 "I will be pleased to help fix this bug, which will be my first commit")
SOFT = re.compile(
    r"(i['’]?d\s*like\s*to\s*(take|implement|fix|work|submit)|"
    r"(?:happy|glad)\s+to\s+(?:fix|implement|help\s+(?:to\s+)?(?:fix|implement)|"
    r"(?:open|prepare|submit|send)\s+(?:a\s+)?(?:pr|pull\s+request))\b|"
    r"i'?m\s*(planning|going)\s*to\s*(contribute|fix|implement)|"
    r"would\s*love\s*to\s*(work|fix|implement)|"
    r"can\s*i\s*take\s*this|i'?ll\s*submit\s*a\s*pr|i\s*will\s*submit\s*a\s*pr|"
    r"(?:working|(?:happy|glad)\s+to\s+work)\s+on\s+"
    r"(?:(?:a|the|this)\s+(?:fix|patch|pr|pull\s+request|issue|bug)|this|it)\b|"
    r"i'?m\s*on\s*it|taking\s*this|claiming\s*this|"
    r"i\s*can\s*take\s*(this|it)|assign\s*(this|it)\s*to\s*me|already\s*(on\s*it|working)|"
    r"i\s*have\s*a\s*(fix|pr)\s*ready|local\s*fix\s*ready|"
    r"would\s*like\s*to\s*implement|i\s*would\s*like\s*to\s*(implement|fix|work|take)|"
    r"i\s*will\s*wait\s*for|waiting\s*for\s*(the\s*)?(preferred|maintainer|green)|"
    r"(be\s*)?pleased\s*to\s*help\s*(to\s*)?(fix)?|help\s*(to\s*)?fix\s*this\s*bug|"
    r"i(?:['’]ll|\s+(?:can|will))\s+(?:(?:open|send|submit|prepare)\s+(?:a\s+)?(?:pr|pull\s+request)|add\s+(?:regression\s+)?tests?)\b|"
    r"i\s*have\s*a\s*patch\b|codex\s+is\s+assisting\b|"
    r"i(?:['’]ll|\s+will)\s+take\b|i\s+plan\s+(?:a\b|to\s+(?:fix|submit))|"
    r"i\s+have\s+a\s+(?:focused\s+)?fix\b|fix\s+and\s+regression\s+tests\s+ready|"
    r"before\s+i\s+open\s+the\s+upstream\s+pr|assign\s+(?:this\s+issue|it)\s+to\b|"
    r"(?:please\s+)?approve\s+the\s+issue|so\s+i\s+can\s+open|"
    r"kindly\s+assign|please\s+assign|(?:may\s+i\s+take|can\s+i\s+take|can\s+i\s+work\s+on)\b|i['’]ll\s+submit\b|"
    r"i\s+(?:would\s+like\s+to\s+)?propose\b|(?:opening|opened|will\s+open)\s+a\s+pr|"
    r"fix\s+(?:is\s+)?ready|have\s+a\s+focused\s+fix|pr\s+is\s+ready|open\s+a\s+focused\s+pr|"
    r"(?:^|\n)\s*/assign(?:\s|$)|happy\s*to\s*send\s*(?:a\s*)?pr\b|"
    r"i(?:['’]d|\s+would)\s+like\s+to\s+pick\b|"
    r"i(?:['’]ll|\s+(?:will|can))\s+(?:do|work\s+on)\s+(?:this|it|(?:a|the)\s+(?:issue|bug|fix|patch))\b|"
    r"i\s+have\s+a\s+pr\b|(?:patch|branch)\s+(?:is\s+)?ready\b|"
    r"waiting\s+for\s+(?:the\s+)?assign(?:ment)?\b|\bassign\s+me\b|"
    r"\bassigned\s+to\s+me\b|\bsubmitted\s+(?:a\s+)?pr\b|"
    r"my\s*first\s*(commit|contribution|pr)|interest\s*in\s*fixing|"
    r"let\s*me\s*(take|fix|try)\s*(this|it)?)", re.I)

NOT_READY = re.compile(
    r"not\s+(?:yet\s+)?ready\s+for\s+(?:a\s+)?(?:pr|pull\s+request)\b|do\s*not\s*(open|submit)\s*a\s*pr|"
    r"wait\s*(for|until)\s*(triage|maintainer)", re.I)

# 标题开头的平台标签：非 Windows 内核的分支在 Windows 本机既装不起也复现不了，直接弃。
# 例(2026-10-29 校正仓名后补扫所得)：giampaolo/psutil#3087 "[macOS] cpu_count() raises
# SystemError"、#3088 "[FreeBSD] sensors_temperatures() ..."，两条均为 C 扩展 + 故障注入。
# 不含 Linux：跨平台的纯 Python 包里 "[Linux]" 常只标出发现环境，核心可能可测，留给人工判。
PLATFORM_ONLY = re.compile(
    r"^\s*[\[(]?\s*(?:mac\s*os\s*x|macos|osx|darwin|freebsd|openbsd|netbsd|dragonfly(?:fly)?bsd|"
    r"aix|solaris|sunos|hp-?ux|android|ios)\s*(?:[\]):]|-)", re.I)


# Resolution hints used by discovery prefilters; not evidence of completed checks.
FIXED_IN_PR = re.compile(
    "|".join(re.escape(p) for p in (
        "fixed by pr", "fixed by #", "resolved by pr", "resolved by #",
        "fixed in pr", "fix reference", "already fixed", "pr that fixes", "opened #"))
    + r"|(?:pr|pull request) #\d+ fixes\b|(?<![\w/#])#\d+ fixes\b", re.IGNORECASE)
