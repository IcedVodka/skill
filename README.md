# Skill 同步仓库

这个仓库用于在不同电脑之间同步个人必备的 Codex skills，并集中记录选装 skills 的安装入口。

## 结构

```text
.
├── <skill-name>/              # 必装：源码随仓库同步
│   └── SKILL.md
├── other skills/
│   ├── <skill-name>/          # 选装：源码收录在仓库中
│   └── <skill-name>.md        # 选装：仅记录外部安装入口
├── AGENTS.md                  # 仓库维护约定
└── README.md
```

根目录中的 skill 是新电脑的必装项；`other skills` 下的所有内容都是选装项。选装项分成两种：文件夹表示仓库保存了 skill 源码，单个 Markdown 文档表示只跟踪上游安装方式，不在本仓库复制源码。

## 必装 skills

- `chinese-writing`
- `gh-cli`
- `github-repo-discovery`
- `grilling`
- `kimi-webbridge`

## 在新电脑上安装

先确保 Codex 已安装，然后使用 Codex 自带的 skill 安装器：

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo IcedVodka/skill \
  --ref master \
  --path chinese-writing gh-cli github-repo-discovery grilling kimi-webbridge
```

安装器默认写入 `~/.codex/skills`。如果某个同名 skill 已存在，安装器会停止以避免覆盖；请先比较版本并备份，再决定保留仓库版还是本机版。

## 选装 skills

选装项及其安装方式见 [`other skills/README.md`](other%20skills/README.md)。

## 日常同步

1. 在一台电脑上更新或新增 skill。
2. 比较仓库版与本机安装版，保留较新内容。
3. 提交并推送仓库改动。
4. 在其他电脑拉取仓库，再安装或更新对应 skill。

具体维护规则见 [`AGENTS.md`](AGENTS.md)。
