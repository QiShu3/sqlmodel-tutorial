#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLModel 字段代码生成工具
基于 GUI 界面的字段定义代码生成器
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Dict, Any, Optional
import json

class FieldGeneratorGUI:
    """SQLModel 字段代码生成器 GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("SQLModel 字段代码生成器")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # 字段类型映射
        self.field_types = {
            "整数 (int)": "int",
            "字符串 (str)": "str",
            "布尔值 (bool)": "bool",
            "浮点数 (float)": "float",
            "精确小数 (Decimal)": "Decimal",
            "日期时间 (datetime)": "datetime",
            "日期 (date)": "date",
            "时间 (time)": "time",
            "UUID": "uuid.UUID",
            "枚举 (Enum)": "Enum",
            "JSON 字典 (Dict)": "Dict[str, Any]",
            "字符串列表 (List[str])": "List[str]"
        }
        
        # 存储字段信息
        self.fields = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="SQLModel 字段代码生成器", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 字段输入区域
        self.create_field_input_section(main_frame)
        
        # 字段列表区域
        self.create_field_list_section(main_frame)
        
        # 代码生成区域
        self.create_code_output_section(main_frame)
        
        # 按钮区域
        self.create_button_section(main_frame)
    
    def create_field_input_section(self, parent):
        """创建字段输入区域"""
        # 字段输入框架
        input_frame = ttk.LabelFrame(parent, text="字段信息输入", padding="10")
        input_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # 字段名称
        ttk.Label(input_frame, text="字段名称:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10))
        self.field_name_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.field_name_var, width=30).grid(row=row, column=1, sticky=(tk.W, tk.E))
        row += 1
        
        # 字段类型
        ttk.Label(input_frame, text="字段类型:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.field_type_var = tk.StringVar()
        type_combo = ttk.Combobox(input_frame, textvariable=self.field_type_var, 
                                 values=list(self.field_types.keys()), state="readonly")
        type_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=(5, 0))
        type_combo.bind('<<ComboboxSelected>>', self.on_type_change)
        row += 1
        
        # 可选性
        ttk.Label(input_frame, text="可选性:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.optional_var = tk.BooleanVar()
        ttk.Checkbutton(input_frame, text="可选字段 (Optional)", 
                       variable=self.optional_var).grid(row=row, column=1, sticky=tk.W, pady=(5, 0))
        row += 1
        
        # 主键
        ttk.Label(input_frame, text="主键:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.primary_key_var = tk.BooleanVar()
        ttk.Checkbutton(input_frame, text="主键字段 (Primary Key)", 
                       variable=self.primary_key_var).grid(row=row, column=1, sticky=tk.W, pady=(5, 0))
        row += 1
        
        # 默认值
        ttk.Label(input_frame, text="默认值:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.default_value_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.default_value_var, width=30).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=(5, 0))
        row += 1
        
        # 描述
        ttk.Label(input_frame, text="描述:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.description_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.description_var, width=30).grid(row=row, column=1, sticky=(tk.W, tk.E), pady=(5, 0))
        row += 1
        
        # 最小值/长度
        ttk.Label(input_frame, text="最小值/长度:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.min_value_var = tk.StringVar()
        self.min_entry = ttk.Entry(input_frame, textvariable=self.min_value_var, width=30)
        self.min_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=(5, 0))
        row += 1
        
        # 最大值/长度
        ttk.Label(input_frame, text="最大值/长度:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.max_value_var = tk.StringVar()
        self.max_entry = ttk.Entry(input_frame, textvariable=self.max_value_var, width=30)
        self.max_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=(5, 0))
        row += 1
        
        # 特殊参数（针对 Decimal 类型）
        ttk.Label(input_frame, text="小数位数:").grid(row=row, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.decimal_places_var = tk.StringVar()
        self.decimal_entry = ttk.Entry(input_frame, textvariable=self.decimal_places_var, width=30)
        self.decimal_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=(5, 0))
        self.decimal_entry.config(state='disabled')
        row += 1
        
        # 添加字段按钮
        ttk.Button(input_frame, text="添加字段", 
                  command=self.add_field).grid(row=row, column=1, sticky=tk.E, pady=(10, 0))
    
    def create_field_list_section(self, parent):
        """创建字段列表区域"""
        list_frame = ttk.LabelFrame(parent, text="已添加字段", padding="10")
        list_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 字段列表
        self.field_listbox = tk.Listbox(list_frame, height=6)
        self.field_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.field_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.field_listbox.configure(yscrollcommand=scrollbar.set)
        
        # 删除按钮
        ttk.Button(list_frame, text="删除选中字段", 
                  command=self.remove_field).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
    
    def create_code_output_section(self, parent):
        """创建代码输出区域"""
        output_frame = ttk.LabelFrame(parent, text="生成的代码", padding="10")
        output_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        # 代码文本区域
        self.code_text = scrolledtext.ScrolledText(output_frame, height=12, width=80)
        self.code_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        parent.rowconfigure(3, weight=1)
    
    def create_button_section(self, parent):
        """创建按钮区域"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="生成代码", 
                  command=self.generate_code).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="清空所有", 
                  command=self.clear_all).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="复制代码", 
                  command=self.copy_code).pack(side=tk.LEFT)
    
    def on_type_change(self, event=None):
        """字段类型改变时的处理"""
        selected_type = self.field_type_var.get()
        
        # 根据类型启用/禁用特定输入框
        if "Decimal" in selected_type:
            self.decimal_entry.config(state='normal')
        else:
            self.decimal_entry.config(state='disabled')
            self.decimal_places_var.set("")
    
    def add_field(self):
        """添加字段到列表"""
        # 验证输入
        if not self.field_name_var.get().strip():
            messagebox.showerror("错误", "请输入字段名称")
            return
        
        if not self.field_type_var.get():
            messagebox.showerror("错误", "请选择字段类型")
            return
        
        # 创建字段信息字典
        field_info = {
            'name': self.field_name_var.get().strip(),
            'type': self.field_types[self.field_type_var.get()],
            'optional': self.optional_var.get(),
            'primary_key': self.primary_key_var.get(),
            'default': self.default_value_var.get().strip() if self.default_value_var.get().strip() else None,
            'description': self.description_var.get().strip() if self.description_var.get().strip() else None,
            'min_value': self.min_value_var.get().strip() if self.min_value_var.get().strip() else None,
            'max_value': self.max_value_var.get().strip() if self.max_value_var.get().strip() else None,
            'decimal_places': self.decimal_places_var.get().strip() if self.decimal_places_var.get().strip() else None
        }
        
        # 添加到字段列表
        self.fields.append(field_info)
        
        # 更新列表显示
        display_text = f"{field_info['name']} ({field_info['type']})"
        if field_info['optional']:
            display_text += " [可选]"
        if field_info['primary_key']:
            display_text += " [主键]"
        
        self.field_listbox.insert(tk.END, display_text)
        
        # 清空输入框
        self.clear_inputs()
        
        messagebox.showinfo("成功", f"字段 '{field_info['name']}' 已添加")
    
    def remove_field(self):
        """删除选中的字段"""
        selection = self.field_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择要删除的字段")
            return
        
        index = selection[0]
        field_name = self.fields[index]['name']
        
        # 删除字段
        del self.fields[index]
        self.field_listbox.delete(index)
        
        messagebox.showinfo("成功", f"字段 '{field_name}' 已删除")
    
    def clear_inputs(self):
        """清空输入框"""
        self.field_name_var.set("")
        self.field_type_var.set("")
        self.optional_var.set(False)
        self.primary_key_var.set(False)
        self.default_value_var.set("")
        self.description_var.set("")
        self.min_value_var.set("")
        self.max_value_var.set("")
        self.decimal_places_var.set("")
        self.decimal_entry.config(state='disabled')
    
    def clear_all(self):
        """清空所有内容"""
        if messagebox.askyesno("确认", "确定要清空所有字段吗？"):
            self.fields.clear()
            self.field_listbox.delete(0, tk.END)
            self.code_text.delete(1.0, tk.END)
            self.clear_inputs()
    
    def generate_code(self):
        """生成字段代码"""
        if not self.fields:
            messagebox.showwarning("警告", "请先添加字段")
            return
        
        # 生成导入语句
        imports = set()
        imports.add("from typing import Optional")
        imports.add("from sqlmodel import SQLModel, Field")
        
        # 根据字段类型添加必要的导入
        for field in self.fields:
            if field['type'] == 'Decimal':
                imports.add("from decimal import Decimal")
            elif field['type'] in ['datetime', 'date', 'time']:
                imports.add("from datetime import datetime, date, time")
            elif field['type'] == 'uuid.UUID':
                imports.add("import uuid")
            elif 'Dict' in field['type'] or 'List' in field['type']:
                imports.add("from typing import Dict, List, Any")
        
        # 生成代码
        code_lines = []
        code_lines.extend(sorted(imports))
        code_lines.append("")
        code_lines.append("class GeneratedModel(SQLModel, table=True):")
        code_lines.append('    """自动生成的模型类"""')
        code_lines.append("")
        
        for field in self.fields:
            field_code = self.generate_field_code(field)
            code_lines.append(f"    {field_code}")
        
        # 显示生成的代码
        self.code_text.delete(1.0, tk.END)
        self.code_text.insert(1.0, "\n".join(code_lines))
        
        messagebox.showinfo("成功", "代码生成完成！")
    
    def generate_field_code(self, field_info: Dict[str, Any]) -> str:
        """生成单个字段的代码"""
        name = field_info['name']
        field_type = field_info['type']
        
        # 处理可选类型
        if field_info['optional']:
            type_annotation = f"Optional[{field_type}]"
        else:
            type_annotation = field_type
        
        # 构建 Field 参数
        field_params = []
        
        # 默认值
        if field_info['default'] is not None:
            if field_info['default'].lower() in ['none', 'null']:
                field_params.append("default=None")
            elif field_info['default'].lower() == 'true':
                field_params.append("default=True")
            elif field_info['default'].lower() == 'false':
                field_params.append("default=False")
            elif field_info['default'].startswith('datetime.'):
                field_params.append(f"default_factory={field_info['default']}")
            elif field_info['default'].startswith('uuid.'):
                field_params.append(f"default_factory={field_info['default']}")
            else:
                try:
                    # 尝试解析为数字
                    float(field_info['default'])
                    field_params.append(f"default={field_info['default']}")
                except ValueError:
                    # 字符串默认值
                    field_params.append(f'default="{field_info["default"]}"')
        elif field_info['optional']:
            field_params.append("default=None")
        
        # 主键
        if field_info['primary_key']:
            field_params.append("primary_key=True")
        
        # 最小值/长度
        if field_info['min_value']:
            if field_type == 'str':
                field_params.append(f"min_length={field_info['min_value']}")
            else:
                field_params.append(f"ge={field_info['min_value']}")
        
        # 最大值/长度
        if field_info['max_value']:
            if field_type == 'str':
                field_params.append(f"max_length={field_info['max_value']}")
            else:
                field_params.append(f"le={field_info['max_value']}")
        
        # Decimal 特殊参数
        if field_type == 'Decimal':
            if field_info['max_value']:
                field_params.append(f"max_digits={field_info['max_value']}")
            if field_info['decimal_places']:
                field_params.append(f"decimal_places={field_info['decimal_places']}")
        
        # 描述
        if field_info['description']:
            field_params.append(f'description="{field_info["description"]}"')
        
        # 构建完整的字段定义
        if field_params:
            field_def = f"Field({', '.join(field_params)})"
        else:
            field_def = "Field()"
        
        return f"{name}: {type_annotation} = {field_def}"
    
    def copy_code(self):
        """复制生成的代码到剪贴板"""
        code = self.code_text.get(1.0, tk.END).strip()
        if not code:
            messagebox.showwarning("警告", "没有可复制的代码")
            return
        
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        messagebox.showinfo("成功", "代码已复制到剪贴板")

def main():
    """主函数"""
    root = tk.Tk()
    app = FieldGeneratorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()