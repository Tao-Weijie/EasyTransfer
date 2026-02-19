# -*- coding: utf-8 -*-
import os
import json
import Rhino
import Rhino.UI
from Eto.Forms import (Dialog, Label, TextBox, Button, 
                       DynamicLayout, FileDialogMode, SelectFolderDialog,
                       MessageBox, MessageBoxType)
from Eto.Drawing import Size

# ==============================================================================
# 1. 后端：JSON 配置管理
# ==============================================================================
class ConfigManager:
    def __init__(self):
        # 配置文件存放在用户的 AppData/Roaming/McNeel... 或者你的插件目录下
        # 这里为了演示，存放在用户文档目录下
        self.config_dir = os.path.join(os.path.expanduser("~"), "Documents", "EasyTransfer")
        self.config_file = os.path.join(self.config_dir, "settings.json")
        
        # 默认设置
        self.default_settings = {
            "export_path": os.path.join(os.path.expanduser("~"), "Desktop"),
            "shortcut_copy": "Ctrl+Shift+C",
            "shortcut_paste": "Ctrl+Shift+V"
        }
        
        self.ensure_config_exists()

    def ensure_config_exists(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        if not os.path.exists(self.config_file):
            self.save_settings(self.default_settings)

    def load_settings(self):
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                # 合并缺少的键值 (防止版本更新后旧配置报错)
                for key, val in self.default_settings.items():
                    if key not in data:
                        data[key] = val
                return data
        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error loading settings: {e}")
            return self.default_settings

    def save_settings(self, settings_dict):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(settings_dict, f, indent=4)
            return True
        except Exception as e:
            Rhino.RhinoApp.WriteLine(f"Error saving settings: {e}")
            return False

# ==============================================================================
# 2. 前端：Eto 设置面板
# ==============================================================================
class EasyTransferSettingsDialog(Dialog[bool]):
    def __init__(self):
        self.Title = "EasyTransfer Settings"
        self.Padding = Rhino.UI.EtoExtensions.Padding(10)
        self.Resizable = False
        self.ClientSize = Size(400, 220)
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        self.current_settings = self.config_manager.load_settings()

        # --- 创建控件 ---
        
        # 1. 路径设置
        self.lbl_path = Label(Text="Export Path:")
        self.txt_path = TextBox(Text=self.current_settings["export_path"])
        self.btn_browse = Button(Text="Browse...")
        self.btn_browse.Click += self.on_browse_click

        # 2. 快捷键显示 (注意：这里主要作为显示/备忘，修改真实快捷键逻辑很复杂)
        self.lbl_short_copy = Label(Text="Copy Shortcut (Info):")
        self.txt_short_copy = TextBox(Text=self.current_settings["shortcut_copy"])
        
        self.lbl_short_paste = Label(Text="Paste Shortcut (Info):")
        self.txt_short_paste = TextBox(Text=self.current_settings["shortcut_paste"])

        # 3. 底部按钮
        self.btn_save = Button(Text="Save & Close")
        self.btn_save.Click += self.on_save_click
        
        self.btn_cancel = Button(Text="Cancel")
        self.btn_cancel.Click += self.on_cancel_click

        # --- 布局 (DynamicLayout 是最简单的排版方式) ---
        layout = DynamicLayout()
        layout.Spacing = Size(5, 5)

        layout.AddRow(self.lbl_path)
        layout.AddRow(self.txt_path, self.btn_browse) # 两个控件放在同一行
        layout.AddRow(None) # 空行间隔
        
        layout.AddRow(self.lbl_short_copy, self.txt_short_copy)
        layout.AddRow(self.lbl_short_paste, self.txt_short_paste)
        
        layout.AddRow(None) # 弹簧，把下面按钮顶到底部
        
        # 底部按钮行
        layout.AddRow(self.btn_save, self.btn_cancel)

        self.Content = layout

    # --- 事件处理 ---

    def on_browse_click(self, sender, e):
        dlg = SelectFolderDialog()
        dlg.Title = "Select Export Folder"
        dlg.Directory = self.txt_path.Text
        if dlg.ShowDialog(self) == DialogResult.Ok:
            self.txt_path.Text = dlg.Directory

    def on_save_click(self, sender, e):
        # 更新字典
        new_settings = {
            "export_path": self.txt_path.Text,
            "shortcut_copy": self.txt_short_copy.Text,
            "shortcut_paste": self.txt_short_paste.Text
        }
        
        # 保存到 JSON
        success = self.config_manager.save_settings(new_settings)
        
        if success:
            MessageBox.Show("Settings saved successfully!", "EasyTransfer", MessageBoxType.Information)
            self.Close(True) # 关闭并返回 True
        else:
            MessageBox.Show("Failed to save settings.", "Error", MessageBoxType.Error)

    def on_cancel_click(self, sender, e):
        self.Close(False) # 关闭并返回 False

# ==============================================================================
# 3. 主程序入口
# ==============================================================================
def show_settings():
    # 实例化并显示对话框
    dlg = EasyTransferSettingsDialog()
    # ShowModal 会阻塞 Rhino 界面直到对话框关闭
    result = dlg.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
    
    if result:
        print("Settings updated.")
        # 这里可以添加逻辑：比如重新加载插件以应用新设置
    else:
        print("Settings cancelled.")

if __name__ == "__main__":
    show_settings()