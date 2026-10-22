<p align="center">
  <a href="README.md">English</a> · <b>简体中文</b> · <a href="README.tr.md">Türkçe</a> · <a href="README.ar.md">العربية</a>
</p>

# python-cli-license-starter

一个用许可证密钥出售 Python 命令行工具的小模板。克隆下来，把 `mytool` 改成你自己的名字，再把你的命令写进 `commands.py`

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE)

<p align="center">
  <img src="docs/terminal.png" alt="Windows Terminal 中的 mytool status 和两次运行，第二次显示了来自后台的消息" width="820">
</p>

授权部分基于 [PWF Auth](https://pwfauth.com)，免费使用。你需要在那里注册一个账号，用来获取应用密钥（app secret）和许可证密钥

这里有一段 3 分钟的真实录屏，从 `git clone` 一直演示到在 exe 运行时封禁密钥：[youtu.be/2tYxlYZwNnc](https://youtu.be/2tYxlYZwNnc)

## 试一试

```bash
git clone https://github.com/pwfauth/python-cli-license-starter.git
cd python-cli-license-starter
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
export PWFAUTH_SECRET=your-app-secret  # PowerShell: $env:PWFAUTH_SECRET = "your-app-secret"
mytool activate YOUR-LICENSE-KEY
mytool run
```

应用密钥在后台 Applications 页面中你的应用卡片上，许可证密钥在 Licences 页面生成

<p align="center">
  <img src="docs/activate.png" alt="mytool activate 将密钥绑定到本机并显示许可证信息" width="820">
</p>

## 包含什么

- `mytool activate` 把密钥绑定到这台电脑，并保存在系统的凭据存储中（Windows 的 Credential Manager、macOS 的 Keychain、Linux 的 Secret Service）
- `mytool trial` 发放免费试用，每台电脑只能用一次
- `mytool status` 查看许可证状态，不占用设备名额。脚本需要时加上 `--json`
- `mytool update` 在你发布新版本时通知用户，并附上更新日志
- `mytool deactivate` 从这台电脑上移除密钥
- `mytool run` 是付费功能部分，换成你自己的代码就行

如果某个密钥已经在另一台电脑上使用，`activate` 会询问是否把它转移到当前电脑。客户能不能自己转移、多久能转一次，都在后台设置

## 运行中远程停用

<p align="center">
  <img src="docs/kill-switch.gif" alt="在后台封禁密钥后，正在运行的 exe 随即停止" width="820">
</p>

付费命令在 `get_licensing().session()` 中运行。代码块执行期间，心跳（heartbeat）会在后台检查密钥。在后台封禁、暂停或删除密钥后，命令会在下一次心跳时停止，退出码为 3

停止的原理：心跳线程调用 `_thread.interrupt_main()`，会话把由此产生的 `KeyboardInterrupt` 转换成 `SessionEnded`。卡在 C 调用里的代码无法被中断，所以 10 秒后进程无论如何都会退出

## 添加你自己的命令

```python
from .cli import app, friendly, get_licensing

@app.command()
@friendly
def convert(path: str) -> None:
    """Convert a folder (paid)"""
    with get_licensing().session() as session:
        for item in load(path):
            process(item)
            session.ensure_active()   # optional, stops between items once the key is revoked
```

`licensing.py` 是唯一和许可证服务器通信的文件，其余代码不需要关心密钥从哪里来

## 状态与更新

<p align="center">
  <img src="docs/dashboard-text.png" alt="PWF Auth 后台 Texts & slides 页面中的 motd 文本" width="820">
</p>

在后台的 Updates 页面发布新版本，`mytool update` 就会显示出来。Texts & slides 页面里的文本也会出现在工具中：示例在每次运行开始时打印名为 `motd` 的文本，这样不发新版本也能通知用户

## 打包成单个可执行文件

```bash
pip install -e ".[build]"
PWFAUTH_SECRET=your-app-secret python scripts/build.py
```

在 Windows 上会生成 `dist/mytool.exe`，其他系统上是 `dist/mytool`。应用密钥只会写入这一次构建。`build/`、`dist/` 和 `src/mytool/_build_secret.py` 都包含密钥，所以它们都在 `.gitignore` 里

发到客户电脑上的任何程序都有可能被修改。服务器会对每个响应签名，伪造的服务器无法解锁工具；但真正有价值的东西，最好放在你自己的服务器上，并在那里校验许可证

## 设置

| 变量 | 用途 |
|---|---|
| `PWFAUTH_SECRET` | 你的应用密钥（发布构建中已内置） |
| `MYTOOL_LICENSE_KEY` | 给 CI 或服务器用的许可证密钥，只在本次运行中使用，不会保存 |
| `MYTOOL_STORE` | `keyring`（默认）或 `file` |
| `MYTOOL_HOME` | 文件存储保存密钥的位置 |

没有凭据存储的机器（比如无界面服务器或容器）会改用一个只有当前用户能读取的文件

退出码：`0` 正常，`1` 配置或网络问题，`2` 没有许可证或被服务器拒绝，`3` 运行中许可证失效，`130` 按下了 Ctrl+C

## 测试

```bash
pytest
```

测试基于 `tests/conftest.py` 中的模拟客户端运行，不需要网络，也不需要账号

## 许可

MIT，详见 [LICENSE](LICENSE)
