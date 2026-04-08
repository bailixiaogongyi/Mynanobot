# AiMate Skills

This directory contains built-in skills that extend AiMate's capabilities.

## Skill Format

Each skill is a directory containing a `SKILL.md` file with:

- YAML frontmatter (name, description, metadata)
- Markdown instructions for the agent

## Attribution

These skills are adapted from [OpenClaw](https://github.com/openclaw/openclaw)'s skill system.
The skill format and metadata structure follow OpenClaw's conventions to maintain compatibility.

## Available Skills

| Skill                | Description                                          |
| -------------------- | ---------------------------------------------------- |
| `github`             | Interact with GitHub using the `gh` CLI              |
| `weather`            | Get weather info using wttr.in and Open-Meteo        |
| `summarize`          | Summarize URLs, files, and YouTube videos            |
| `tmux`               | Remote-control tmux sessions                         |
| `clawhub`            | Search and install skills from ClawHub registry      |
| `skill-creator`      | Create new skills                                    |
| `memory`             | 记忆管理，存储和检索重要信息                         |
| `cron`               | 定时任务管理                                         |
| `daily-note`         | 每日笔记                                             |
| `project-note`       | 项目笔记                                             |
| `topic-note`         | 主题笔记                                             |
| `temp-note`          | 临时笔记                                             |
| `archive`            | 归档管理                                             |
| `word-operations`    | Word文档操作，读取内容、调整样式、表格操作、模板生成 |
| `vision-operations`  | 图片内容识别和文生图操作，支持图片分析和AI生成图片   |
