"""AI-assisted local desktop launcher for portrait_to_pawn.py."""
from datetime import datetime
from pathlib import Path
import os
import queue
import re
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from portrait_to_pawn import HERE, generate


class App:
    def __init__(self,root):
        self.root=root;root.title('PortraitToPawn · 立绘转躯干草稿');root.geometry('1040x840')
        self.source=tk.StringVar(value=sys.argv[1] if len(sys.argv)>1 else '')
        self.name=tk.StringVar(value='');self.family=tk.StringVar(value='自动判断')
        self.sleeve=tk.StringVar(value='肩部短段')
        self.recipe=tk.StringVar();self.status=tk.StringVar(value='选择含服装的单人立绘，再点击生成。')
        self.events=queue.Queue();self.last_output=None;self.photo=None
        self.families={'自动判断':'auto','衬衫＋马甲':'shirt_vest','外套':'coat','连衣裙':'dress'}
        panel=ttk.Frame(root,padding=18);panel.pack(fill='both',expand=True)
        ttk.Label(panel,text='立绘 → RimWorld 躯干贴图',font=('Microsoft YaHei UI',19,'bold')).pack(anchor='w')
        ttk.Label(panel,text='本地生成 256×256 透明 PNG；支持扁平 Q 版及贴身战术配方。').pack(anchor='w',pady=(5,14))
        files=ttk.Frame(panel);files.pack(fill='x')
        ttk.Label(files,text='人物立绘').grid(row=0,column=0,sticky='w',padx=(0,8))
        ttk.Entry(files,textvariable=self.source).grid(row=0,column=1,sticky='ew')
        ttk.Button(files,text='选图…',command=self.select_source).grid(row=0,column=2,padx=(8,0))
        ttk.Label(files,text='覆盖配方').grid(row=1,column=0,sticky='w',padx=(0,8),pady=8)
        ttk.Entry(files,textvariable=self.recipe).grid(row=1,column=1,sticky='ew')
        ttk.Button(files,text='选 JSON…',command=self.select_recipe).grid(row=1,column=2,padx=(8,0))
        files.columnconfigure(1,weight=1)
        options=ttk.Frame(panel);options.pack(fill='x',pady=(4,10))
        ttk.Label(options,text='资源英文名').pack(side='left')
        ttk.Entry(options,textvariable=self.name,width=24).pack(side='left',padx=(8,22))
        ttk.Label(options,text='服装结构').pack(side='left')
        ttk.Combobox(options,textvariable=self.family,values=list(self.families),state='readonly',width=18).pack(side='left',padx=8)
        ttk.Label(options,text='袖口').pack(side='left',padx=(8,0))
        ttk.Combobox(options,textvariable=self.sleeve,values=['肩部短段','不画袖口'],state='readonly',width=10).pack(side='left',padx=8)
        self.run_button=ttk.Button(options,text='读取立绘并生成',command=self.start);self.run_button.pack(side='right')
        ttk.Label(panel,textvariable=self.status,wraplength=970).pack(anchor='w',pady=(3,10))
        self.image_label=ttk.Label(panel,anchor='center',text='生成后在这里预览正面、侧面和背面。')
        self.image_label.pack(fill='both',expand=True)
        controls=ttk.Frame(panel);controls.pack(fill='x',pady=(10,0))
        self.open_button=ttk.Button(controls,text='打开本次输出目录',command=self.open_output,state='disabled');self.open_button.pack(side='left')
        ttk.Button(controls,text='查看使用说明',command=lambda:os.startfile(HERE/'使用说明.txt')).pack(side='left',padx=8)
        ttk.Label(panel,text='躯干不画双臂或手；头部另行处理。侧背和未展示的裤装采用推断；每次输出到新目录。',wraplength=980).pack(anchor='w',pady=(10,0))
        root.after(100,self.poll)

    def select_source(self):
        path=filedialog.askopenfilename(title='选择人物立绘',filetypes=[('图片','*.png *.jpg *.jpeg *.webp'),('所有文件','*.*')])
        if path:
            self.source.set(path)
            stem=re.sub(r'(Portrait|Stand)$','',Path(path).stem)
            if re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',stem):self.name.set(stem)

    def select_recipe(self):
        path=filedialog.askopenfilename(title='可选：覆盖配方',filetypes=[('JSON','*.json')])
        if path:self.recipe.set(path)

    def start(self):
        if not Path(self.source.get()).is_file():
            messagebox.showerror('未找到立绘','请先选择一个存在的图片文件。');return
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',self.name.get()):
            messagebox.showerror('请输入资源英文名','使用英文字母开头，后接字母、数字或下划线，最多 64 字符。');return
        self.run_button.configure(state='disabled');self.status.set('正在分析颜色并合成三向躯干…')
        args=(self.source.get(),self.name.get(),self.families[self.family.get()],self.recipe.get(),
              'short' if self.sleeve.get()=='肩部短段' else 'none')
        threading.Thread(target=self.work,args=args,daemon=True).start()

    def work(self,source,name,family,recipe,sleeve_style):
        try:
            stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            dest,profile=generate(source,HERE/'exports'/f'{name}_{stamp}',name,family,recipe or None,
                                  HERE.parents[2]/'MIS_arknights'/'Textures'/'Things'/'AK_Agents',sleeve_style)
            self.events.put(('done',dest,profile))
        except Exception as exc:self.events.put(('error',str(exc)))

    def poll(self):
        try:
            event=self.events.get_nowait();self.run_button.configure(state='normal')
            if event[0]=='error':
                self.status.set('生成失败，请按提示调整输入。');messagebox.showerror('生成失败',event[1])
            else:
                _,dest,profile=event;self.last_output=dest
                im=Image.open(dest/'body_preview.png');im.thumbnail((970,530),Image.Resampling.LANCZOS)
                self.photo=ImageTk.PhotoImage(im);self.image_label.configure(image=self.photo,text='')
                self.status.set(f"已完成：{profile['family']}。文件：{dest}")
                self.open_button.configure(state='normal')
        except queue.Empty:pass
        self.root.after(100,self.poll)

    def open_output(self):
        if self.last_output:os.startfile(self.last_output)


if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()
