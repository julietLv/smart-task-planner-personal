import { marked } from 'marked'

// ⭐ 配置 GFM（与 ChatWindow.vue 保持一致）
marked.use({
  gfm: true,
  breaks: true
})

console.log('=== Marked 表格解析测试 ===\n')

// 测试 1：简单表格
const testTable1 = `| A | B | C |
|---|---|---|
| 1 | 2 | 3 |
| 4 | 5 | 6 |`

console.log('测试 1 - 简单表格:')
console.log('输入:', testTable1)
console.log('\n输出 HTML:')
console.log(marked.parse(testTable1))
console.log('\n是否包含 <table>:', marked.parse(testTable1).includes('<table>'))
console.log('\n' + '='.repeat(80) + '\n')

// 测试 2：周报中的实际表格格式
const testTable2 = `| 日期 | 星期 | 完成任务 | 总任务 | 完成率 |
|------|------|---------|--------|--------|
| 2026-05-21 | 周四 | 1 | 3 | 33.3% |
| 2026-05-22 | 周五 | 0 | 5 | 0.0% |`

console.log('测试 2 - 周报表格:')
console.log('输入:', testTable2)
console.log('\n输出 HTML:')
const html2 = marked.parse(testTable2)
console.log(html2)
console.log('\n是否包含 <table>:', html2.includes('<table>'))
console.log('是否包含 <thead>:', html2.includes('<thead>'))
console.log('是否包含 <tbody>:', html2.includes('<tbody>'))
console.log('\n' + '='.repeat(80) + '\n')

// 测试 3：完整的周报 Markdown
const fullReport = `# 📊 本周工作周报

## 📈 每日完成情况

| 日期 | 星期 | 完成任务 | 总任务 | 完成率 |
|------|------|---------|--------|--------|
| 2026-05-21 | 周四 | 1 | 3 | 33.3% |
| 2026-05-22 | 周五 | 0 | 5 | 0.0% |

## 💡 建议

- 提高工作效率
- 合理安排时间`

console.log('测试 3 - 完整周报:')
console.log('输入长度:', fullReport.length, '字符')
console.log('\n输出 HTML (前 500 字符):')
const html3 = marked.parse(fullReport)
console.log(html3.substring(0, 500))
console.log('\n...')
console.log('\n是否包含 <table>:', html3.includes('<table>'))
console.log('是否包含 <th>日期</th>:', html3.includes('<th>日期</th>') || html3.includes('<td>日期</td>'))
console.log('\n' + '='.repeat(80) + '\n')

// 总结
console.log('✅ 测试完成！')
console.log('\n如果所有测试都显示 "是否包含 <table>: true"，说明 marked 配置正确。')
console.log('如果显示 false，说明需要检查 marked 配置或版本。')
