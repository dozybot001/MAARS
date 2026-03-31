# MAARS Release Notes 模板

release body 不要重复 release 标题。GitHub release 的标题单独填写。

在最终 GitHub release 正文中，这个中文部分应放在英文部分之后，并包在下面这个折叠块里：

```md
<details>
<summary>中文</summary>

...这里填写中文内容...

</details>
```

默认正文应尽量短，目标是让读者在大约 15 秒内看懂这次发布。

## 摘要

用一小段话说明这次发布在实际使用层面意味着什么。

## 变更内容

### Added

- 新增项

### Changed

- 调整项

### Fixed

- 修复项

## 验证

- `pytest tests/ -q`
- `cd frontend && npm run build`

## 说明（可选）

- 只有在确实存在迁移说明、已知边界或运维提醒时才保留这一节。
- 如果没有有价值的信息，就整节省略。
