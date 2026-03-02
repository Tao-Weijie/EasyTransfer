# -*- coding: utf-8 -*-
import os
import json
import Rhino
import Rhino.UI

# --------------------------------------------------------------------------
# [修正] 移除了 FileDialogMode，保留了必要的组件
# --------------------------------------------------------------------------
from Eto.Forms import (Dialog, Label, TextBox, Button, 
                       DynamicLayout, SelectFolderDialog,
                       MessageBox, MessageBoxType, DialogResult) 
from Eto.Drawing import Size

# ==============================================================================
# 1. 后端：JSON 配置管理
# ==============================================================================
class ConfigManager:
    def __init__(self):
        # 配置文件路径
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
            try:
                os.makedirs(self.config_dir)
            except OSError:
                pass 
        if not os.path.exists(self.config_file):
            self.save_settings(self.default_settings)

    def load_settings(self):
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                for key, val in self.default_settings.items():
                    if key not in data:
                        data[key] = val
                return data
        except Exception as e:
            Rhino.RhinoApp.WriteLine(str(e))
            return self.default_settings

    def save_settings(self, settings_dict):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(settings_dict, f, indent=4)
            return True
        except Exception as e:
            Rhino.RhinoApp.WriteLine(str(e))
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
        
        self.config_manager = ConfigManager()
        self.current_settings = self.config_manager.load_settings()

        # --- 创建控件 ---
        self.lbl_path = Label(Text="Export Path:")
        self.txt_path = TextBox(Text=self.current_settings["export_path"])
        self.btn_browse = Button(Text="Browse...")
        self.btn_browse.Click += self.on_browse_click

        self.lbl_short_copy = Label(Text="Copy Shortcut (Info):")
        self.txt_short_copy = TextBox(Text=self.current_settings["shortcut_copy"])
        
        self.lbl_short_paste = Label(Text="Paste Shortcut (Info):")
        self.txt_short_paste = TextBox(Text=self.current_settings["shortcut_paste"])

        self.btn_save = Button(Text="Save & Close")
        self.btn_save.Click += self.on_save_click
        
        self.btn_cancel = Button(Text="Cancel")
        self.btn_cancel.Click += self.on_cancel_click

        # --- 布局 ---
        layout = DynamicLayout()
        layout.Spacing = Size(5, 5)

        layout.AddRow(self.lbl_path)
        layout.AddRow(self.txt_path, self.btn_browse)
        layout.AddRow(None) 
        
        layout.AddRow(self.lbl_short_copy, self.txt_short_copy)
        layout.AddRow(self.lbl_short_paste, self.txt_short_paste)
        
        layout.AddRow(None)
        
        layout.AddRow(self.btn_save, self.btn_cancel)

        self.Content = layout

    # --- 事件处理 ---

    def on_browse_click(self, sender, e):
        dlg = SelectFolderDialog()
        dlg.Title = "Select Export Folder"
        dlg.Directory = self.txt_path.Text
        # 使用 DialogResult 判断点击结果
        if dlg.ShowDialog(self) == DialogResult.Ok:
            self.txt_path.Text = dlg.Directory

    def on_save_click(self, sender, e):
        new_settings = {
            "export_path": self.txt_path.Text,
            "shortcut_copy": self.txt_short_copy.Text,
            "shortcut_paste": self.txt_short_paste.Text
        }
        
        success = self.config_manager.save_settings(new_settings)
        
        if success:
            MessageBox.Show("Settings saved successfully!", "EasyTransfer", MessageBoxType.Information)
            self.Close(True)
        else:
            MessageBox