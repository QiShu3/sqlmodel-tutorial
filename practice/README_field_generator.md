# SQLModel 字段代码生成器

这是一个基于 tkinter 的图形用户界面工具，用于自动生成 SQLModel 字段定义代码。该工具可以帮助开发者快速创建符合 SQLModel 规范的字段定义。

## 功能特性

### 支持的字段类型

- **整数 (int)**: 整数类型字段
- **字符串 (str)**: 字符串类型字段
- **布尔值 (bool)**: 布尔类型字段
- **浮点数 (float)**: 浮点数类型字段
- **精确小数 (Decimal)**: 用于金额等需要精确计算的场景
- **日期时间 (datetime)**: 完整的日期时间
- **日期 (date)**: 仅日期
- **时间 (time)**: 仅时间
- **UUID**: 唯一标识符
- **枚举 (Enum)**: 枚举类型
- **JSON 字典 (Dict)**: 存储复杂数据结构
- **字符串列表 (List[str])**: 字符串数组

### 字段配置选项

1. **字段名称**: 字段的变量名
2. **字段类型**: 从预定义类型中选择
3. **可选性**: 设置字段是否为可选 (Optional)
4. **主键**: 标记字段为主键
5. **默认值**: 设置字段的默认值
6. **描述**: 字段的说明文档
7. **最小值/长度**: 数值的最小值或字符串的最小长度
8. **最大值/长度**: 数值的最大值或字符串的最大长度
9. **小数位数**: 仅适用于 Decimal 类型

## 使用方法

### 启动应用

```bash
python practice/field_generator_gui.py
```

### 操作步骤

1. **填写字段信息**:
   - 输入字段名称
   - 选择字段类型
   - 配置可选性和主键设置
   - 设置默认值（可选）
   - 添加字段描述（可选）
   - 设置约束条件（最小/最大值等）

2. **添加字段**:
   - 点击「添加字段」按钮将字段加入列表
   - 可以添加多个字段

3. **管理字段**:
   - 在字段列表中选择字段并点击「删除选中字段」来移除
   - 使用「清空所有」按钮清除所有字段

4. **生成代码**:
   - 点击「生成代码」按钮生成完整的 SQLModel 类代码
   - 使用「复制代码」按钮将代码复制到剪贴板

## 生成代码示例

### 输入示例

假设我们要创建一个用户模型，包含以下字段：

1. **id**: 整数，主键，可选
2. **username**: 字符串，最大长度50，必填
3. **email**: 字符串，最大长度100，可选
4. **age**: 整数，最小值0，最大值150，可选
5. **balance**: 精确小数，最大10位数，2位小数，默认值0.00
6. **is_active**: 布尔值，默认True
7. **created_at**: 日期时间，默认当前时间

### 生成的代码

```python
from datetime import datetime, date, time
from decimal import Decimal
from sqlmodel import SQLModel, Field
from typing import Optional

class GeneratedModel(SQLModel, table=True):
    """自动生成的模型类"""

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50)
    email: Optional[str] = Field(default=None, max_length=100)
    age: Optional[int] = Field(default=None, ge=0, le=150)
    balance: Decimal = Field(default=0.00, max_digits=10, decimal_places=2)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

## 特殊类型说明

### Decimal 类型

对于 Decimal 类型，工具提供了特殊的配置选项：
- **最大值/长度**: 设置 `max_digits`（总位数）
- **小数位数**: 设置 `decimal_places`（小数位数）

### 默认值处理

工具智能处理不同类型的默认值：
- **None/null**: 转换为 `default=None`
- **true/false**: 转换为 `default=True/False`
- **数字**: 直接使用数值
- **字符串**: 添加引号
- **datetime.utcnow**: 转换为 `default_factory=datetime.utcnow`
- **uuid.uuid4**: 转换为 `default_factory=uuid.uuid4`

### 约束条件

- **字符串类型**: `min_value/max_value` 转换为 `min_length/max_length`
- **数值类型**: `min_value/max_value` 转换为 `ge/le`（大于等于/小于等于）

## 技术实现

### 依赖库

- **tkinter**: GUI 界面框架
- **typing**: 类型注解支持
- **json**: 数据序列化（预留功能）

### 核心功能

1. **字段类型映射**: 将用户友好的类型名称映射到 Python 类型
2. **代码生成引擎**: 根据字段配置生成符合 SQLModel 规范的代码
3. **智能导入**: 根据使用的类型自动生成必要的导入语句
4. **约束处理**: 智能处理不同类型的约束条件

## 扩展功能

### 未来可能的增强

1. **模板保存/加载**: 保存常用的字段配置模板
2. **批量导入**: 从 CSV 或 JSON 文件批量导入字段定义
3. **代码预览**: 实时预览生成的代码
4. **关系字段**: 支持外键和关系字段的定义
5. **索引配置**: 支持数据库索引的配置
6. **验证器**: 支持自定义验证器的添加

## 注意事项

1. **字段名称**: 必须符合 Python 变量命名规范
2. **类型选择**: 确保选择的类型适合你的数据需求
3. **约束条件**: 数值约束仅适用于数值类型，长度约束仅适用于字符串类型
4. **默认值**: 确保默认值与字段类型兼容

## 故障排除

### 常见问题

1. **应用无法启动**: 确保已安装 Python 和 tkinter
2. **字段添加失败**: 检查字段名称和类型是否正确填写
3. **代码生成错误**: 验证字段配置是否合理

### 错误处理

工具包含完善的错误处理机制：
- 输入验证
- 用户友好的错误提示
- 操作确认对话框

---

这个工具旨在提高 SQLModel 开发效率，减少手动编写重复代码的工作量。通过图形界面的直观操作，即使是初学者也能快速生成规范的字段定义代码。