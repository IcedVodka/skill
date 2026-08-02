# 仓库维护说明

本仓库用于在不同电脑之间同步个人常用的 Codex skills。处理本仓库时始终使用简体中文沟通。

## 目录约定

- 仓库根目录下带 `SKILL.md` 的文件夹是必装 skill，应随本仓库同步。
- `other skills/<name>/` 是已收录源码的选装 skill。
- `other skills/<name>.md` 是外部选装 skill 的安装索引，只记录可信来源、安装命令和验证方式，不复制第三方源码。
- `other skills/README.md` 维护选装 skill 的目录。

## 同步规则

1. 比较仓库版本与本机已安装版本时，优先使用 `SKILL.md` frontmatter 中的版本号；没有版本号时，再结合内容差异、上游提交时间和本地文件时间判断。
2. 两侧不一致时保留较新的版本，不得仅凭文件数量判断新旧。
3. 更新根目录中的必装 skill 后，同步更新根 `README.md` 的清单。
4. 新增选装源码时放入 `other skills/<name>/`；只需引导用户前往上游安装时，新增 `other skills/<name>.md`。
5. 外部安装索引必须包含官方或可信上游链接、前置条件、安装步骤、验证命令和核验日期。
6. 不要把密钥、登录信息、机器专属绝对路径或生成文件提交到仓库。

## 提交前检查

- 运行 `git diff --check`。
- 确认所有 `SKILL.md` 都有合法的 YAML frontmatter，至少包含 `name` 和 `description`。
- 检查 README 中的相对链接可用。
- 只提交当前任务相关文件，不覆盖用户的其他改动。
