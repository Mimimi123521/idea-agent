# 灵感管家 - 数据恢复说明

本目录用于存放从旧平台（Railway）导出的数据，供迁移到新服务器时恢复。

## 迁移方式

将本目录中的数据库文件（如 `ideas.db`）复制到服务器应用的数据目录：

```bash
# 在服务器上，覆盖数据文件（先停止服务）
sudo systemctl stop idea-agent
sudo cp /root/import/ideas.db /opt/idea-agent/data/ideas.db
sudo systemctl start idea-agent
```

## 当前包含的数据

| 文件 | 说明 |
|------|------|
| `import_ideas.db` | 从旧环境导出的完整数据库（含灵感/提醒/复盘），可直接改名使用 |

> 说明：当前这份数据来自开发环境的备份。如 Railway 旧数据无法通过公网取出，
> 可用此份作为迁移后的初始数据；后续在阿里云服务器上继续正常记录。