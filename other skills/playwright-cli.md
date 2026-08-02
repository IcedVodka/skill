# Playwright CLI Skill（选装）

用于通过命令行驱动真实浏览器，完成页面导航、交互、快照、截图、网络检查和 UI 流程调试。本仓库不复制该 skill 的源码，以便安装时直接跟随微软官方版本。

## 官方来源

- 仓库：<https://github.com/microsoft/playwright-cli>
- Skill：<https://github.com/microsoft/playwright-cli/tree/main/skills/playwright-cli>
- npm 包：`@playwright/cli`

## 前置条件

- Node.js 18 或更高版本
- npm

## 推荐安装方式

安装最新版 CLI，再让 CLI 安装配套 skills：

```bash
npm install -g @playwright/cli@latest
playwright-cli install --skills
```

验证：

```bash
playwright-cli --help
```

## 仅安装 Skill 到 Codex

如果已经有可用的 `playwright-cli`，也可以用 Codex 自带的安装器直接获取官方 skill：

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo microsoft/playwright-cli \
  --path skills/playwright-cli
```

Codex skill 安装器遇到已存在的同名目录时会停止，不会覆盖现有版本。

## 维护信息

- 许可协议：Apache-2.0
- 上游核验日期：2026-08-02
- 选择理由：微软官方维护、直接提供标准 `SKILL.md`，且仓库仍保持活跃。
