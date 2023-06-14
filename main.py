import os
import pandas as pd
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
import tkinter.messagebox as tkMessageBox
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
import numpy as np
import clipboard

def str_to_num(s):
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s
# 获取当前工作目录
current_path = os.getcwd()
# 获取data目录下的四个数据文件路径
station_path = os.path.join(current_path, "data", "测量站表.csv")
place_path = os.path.join(current_path, "data", "地点表.csv")
sensor_path = os.path.join(current_path, "data", "传感器表.csv")
record_path = os.path.join(current_path, "data", "测量记录表.csv")

class Model():
    """
    这个类用来存储、管理数据，为前端提供数据接口
    """

    def __init__(self) -> None:
        """初始化数据模型"""
        self.station_df = None
        self.place_df = None
        self.sensor_df = None
        self.record_df = None
        self.eng2chs = {"station": "测量站", "place": "地点", "sensor": "传感器", "record": "测量记录"}
        self.order = ["station", "place", "sensor", "record"] # 层级表
        self.name_list = ["测量站", "地点", "传感器", "测量记录"] # 名称表
        self.load_df()

    def load_df(self):
        """重载数据"""
        data_dir = os.path.join(current_path, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        data_files = [
            {"path": station_path, "header": "id,测量站名称,代表地区,测量站状态\n", "table_name": "station"},
            {"path": place_path, "header": "id,地点编号,经度,纬度,海拔,地点状态,测量站ID\n", "table_name": "place"},
            {"path": sensor_path, "header": "id,传感器类型,测量值单位,传感器编号,上线时间,下线时间,传感器状态,地点ID\n", "table_name": "sensor"},
            {"path": record_path, "header": "id,时间,测量值,传感器ID\n", "table_name": "record"}
        ]
        for file in data_files:
            path = file["path"]
            header = file["header"]
            table_name = file["table_name"] + "_df"
            # 检查数据文件是否存在，如果不存在则创建
            if not os.path.exists(path):
                with open(path, 'w', encoding="utf-8") as f:
                    f.write(header)
            # 尝试读取数据文件，如果文件为空则写入表头，如果文件格式错误则删除文件并重新写入表头
            try:
                setattr(self, table_name, pd.read_csv(path))
            except pd.errors.EmptyDataError:
                with open(path, 'w', encoding="utf-8") as f:
                    f.write(header)
                setattr(self, table_name, pd.read_csv(path))
            except pd.errors.ParserError:
                os.remove(path)
                with open(path, 'w', encoding="utf-8") as f:
                    f.write(header)
                setattr(self, table_name, pd.read_csv(path))
    
    def save_df(self):
        """保存数据"""
        self.station_df.to_csv(station_path, index=False)
        self.place_df.to_csv(place_path, index=False)
        self.sensor_df.to_csv(sensor_path, index=False)
        self.record_df.to_csv(record_path, index=False)

    # 定义一个类内异常类：删除违反参照完整性
    class DelReferentialIntegrityError(Exception):
        """违反参照完整性"""
        def __init__(self, table_name : str, id : int, ref_table_name : str, ids : list) -> None:
            self.table_name = table_name
            self.id = id
            self.ref_table_name = ref_table_name
            self.ids = ids
        def __str__(self) -> str:
            return f"删除违反参照完整性：{self.table_name}表中的id为{self.id}的数据被{self.ref_table_name}表中id为{self.ids}的数据作为外键引用"
    # 定义一个类内异常类：外键不存在
    class ForeignKeyNotExistError(Exception):
        """外键不存在"""
        def __init__(self, table_name : str, ref_table_name : str, foreign_id : int) -> None:
            self.table_name = table_name
            self.ref_table_name = ref_table_name
            self.foreign_id = foreign_id
        def __str__(self) -> str:
            return f"外键不存在：{self.table_name}表中引用的外键\"{self.ref_table_name}ID={self.foreign_id}\"不存在"
    # 定义一个类内异常类：索引不存在
    class IndexNotExistError(Exception):
        """索引不存在"""
        def __init__(self, table_name : str, index : str) -> None:
            self.table_name = table_name
            self.index = index
        def __str__(self) -> str:
            return f"索引不存在：{self.table_name}表中的索引\"{self.index}\"不存在"
    class FieldNotExistError(Exception):
        """字段不存在"""
        def __init__(self, table_name : str, field : str) -> None:
            self.table_name = table_name
            self.field = field
        def __str__(self) -> str:
            return f"字段不存在：{self.table_name}表中的字段\"{self.field}\"不存在"

    # 接下来写增删查改的方法

    def query(self, table_name, return_df = False, orient = "split", **kwargs) -> list:
        """查询数据，字段允许接受单个值、二元元组代表范围、列表"""
        # 判断table_name是否为str，如果是则转换为对应的df视图
        if isinstance(table_name, str):
            df = getattr(self, table_name + "_df")
        else:
            df = table_name
        for key, value in kwargs.items():
            if isinstance(value, tuple):
                left, right = value
                # 判断有无空字符串
                if left == "" and right == "":
                    continue
                elif left == "":
                    df = df[df[key] <= right]
                elif right == "":
                    df = df[df[key] >= left]
                else:
                    df = df[(df[key] >= left) & (df[key] <= right)]
            elif isinstance(value, list):
                df = df[df[key].isin(value)]
            else:
                df = df[df[key] == value]
        return df if return_df else df.to_dict(orient=orient)
    
    def insert(self, table_name: str, **kwargs):
        """插入数据"""
        # 检查外键是否存在
        self.raise_foreign_key(table_name, kwargs)
        # 拿到df视图
        df = getattr(self, table_name + "_df")
        new_id = df["id"].max()
        if new_id != new_id :
            new_id = 0
        else:
            new_id += 1
        kwargs["id"] = new_id
        df = pd.concat([df, pd.DataFrame([kwargs])], ignore_index=True)
        setattr(self, table_name + "_df", df)
        self.save_df()
    
    def update(self, table_name : str, id : int, **kwargs):
        """更新数据"""
        df = getattr(self, table_name + "_df")
        # 检查id是否存在，如果不存在，引发索引不存在异常
        if id not in df["id"].values:
            raise self.IndexNotExistError(self.eng2chs[table_name], id)
        # 如果修改了外键，检查外键是否存在
        index = self.order.index(table_name)
        zh_ref_table_name = self.name_list[index - 1]
        if zh_ref_table_name + "ID" in kwargs.keys():
            self.raise_foreign_key(table_name, kwargs)
        df.loc[df["id"] == id, kwargs.keys()] = list(kwargs.values())
        setattr(self, table_name + "_df", df)
        self.save_df()

    def delete(self, table_name : str, ids : list):
        """删除数据"""
        df = getattr(self, table_name + "_df")
        if not isinstance(ids, list):
            ids = [ids]
        for id in ids:
            # 检查id是否存在，如果不存在，跳过本轮循环
            if id not in df["id"].values:
                continue
            result = self.get_foreign_key(table_name, id)
            if result[1]:
                raise self.DelReferentialIntegrityError(self.eng2chs[table_name], id, result[0], result[1])
        df = df[~df["id"].isin(ids)]
        setattr(self, table_name + "_df", df)
        self.save_df()

    # 检查给定表主键是否被其他表作为外键引用，若有则返回其他表中引用项的id
    def get_foreign_key(self, table_name : str, id : int) -> list:
        """检查给定表主键是否被其他表作为外键引用"""
        # 如果是record表，直接返回空列表
        if table_name == "record":
            return (None,[])
        # 获取给定表的层次顺序
        table_order = self.order.index(table_name)
        # 获取下一层次表的df对象
        df = getattr(self, self.order[table_order + 1] + "_df")
        # 对下一层次表进行筛选，找到外键为给定id的项
        df = df[df[self.name_list[table_order] + "ID"] == id]
        # 获取下一层次表的id列表
        id_list = df["id"].tolist()
        # 返回下一层次表的id列表
        return (self.name_list[table_order+1],id_list)
    
    # 检查外键是否存在
    def check_foreign_key(self, table_name : str, foreign_id : int) -> bool:
        """检查外键是否存在"""
        # 如果是station表，直接返回True
        if table_name == "station":
            return True
        # 获取给定表的层次顺序
        table_order = self.order.index(table_name)
        # 获取上一层次表的df对象
        df = getattr(self, self.order[table_order - 1] + "_df")
        # 对上一层次表进行筛选，找到id为给定外键的项
        df = df[df["id"] == foreign_id]
        # 获取上一层次表的id列表
        id_list = df["id"].tolist()
        # 如果id列表为空，则返回False，否则返回True
        return len(id_list) != 0

    # 引发外键不存在的异常
    def raise_foreign_key(self,table_name : str, kwargs : dict):
        # 检查外键是否存在
        index = self.order.index(table_name)
        zh_ref_table_name = self.name_list[index - 1]
        zh_table_name = self.name_list[index]
        foreign_id = kwargs.get(zh_ref_table_name + "ID", None)
        if not self.check_foreign_key(table_name, foreign_id):
            raise self.ForeignKeyNotExistError(zh_table_name, zh_ref_table_name, foreign_id)

    # 接下来写联表查询的方法，使用循环结构根据层次表顺序向前联合查询，使用merge方法
    def union_query(self, table_name : str, return_df = False, orient = "split", **kwargs):
        """向前联表查询"""
        index = self.order.index(table_name)
        df = getattr(self, table_name + "_df")
        for i in range(index-1,-1,-1):
            # 依次左连接表，并删除多余的id列
            df = pd.merge(df, getattr(self, self.order[i] + "_df"), left_on=self.name_list[i] + "ID", right_on="id", how="left", suffixes=("", "_drop")).drop(columns=["id_drop"])
        return self.query(df, return_df, orient, **kwargs)
    
    # 写一个获取表字段的方法
    def get_fields(self, table_name : str):
        """获取表字段"""
        df = getattr(self, table_name + "_df")
        return df.columns.tolist()
    
    # 写一个筛选字段的方法（还可以给字段排序）
    def filter_field(self, df, fields : list, return_df = False, orient = "split"):
        """筛选字段"""
        # 判断df是否为dict列表，若是则转换为DataFrame
        if isinstance(df, list):
            df = pd.DataFrame(df)
        # 捕获异常，如果字段不存在，抛出异常
        try:
            return df[fields] if return_df else df[fields].to_dict(orient=orient)
        except KeyError as e:
           raise self.FieldNotExistError(e.args[0], e.args[1])
        
# 下面开发GUI可视化界面
# 导入一个自定义组件
class ToolTip:
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        """Display text in tooltip window"""
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 57
        y = y + cy + self.widget.winfo_rooty() + 27
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.overrideredirect(1)
        tw.geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                      background="#ffffe0", relief=tk.SOLID, borderwidth=1)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()
    
class PlaceholderEntry(tk.Entry):
    def __init__(self, master=None, placeholder="PLACEHOLDER", color='grey', command=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['fg']
        self.toolTip = ToolTip(self)
        self.bind("<FocusIn>", self.focus_in)
        self.bind("<FocusOut>", self.focus_out)
        self.ForceDisabled = False
        # 加入command 参数
        if command:
            self.bind('<Button-3>', command)
        self.put_placeholder()

    # 重写config方法，使得可以使用config方法修改placeholder、placeholder_color、command
    def config(self, placeholder=None, placeholder_color=None, command=None, *args, **kwargs):
        if placeholder:
            self.placeholder = placeholder
        if placeholder_color:
            self.placeholder_color = placeholder_color
        if command:
            self.bind('<Button-3>', command)
    # 重写get方法，使得当获取到的值为placeholder时，返回空字符串
    def get(self):
        if self['fg'] == self.placeholder_color:
            return ''
        return super().get()

    def put_placeholder(self):
        self.insert(0, self.placeholder)
        self['fg'] = self.placeholder_color

    def focus_in(self, *args):
        if self['fg'] == self.placeholder_color:
            self.delete('0', 'end')
            self['fg'] = self.default_fg_color
        self.toolTip.showtip(self.placeholder)

    def focus_out(self, *args):
        if not self.get():
            self.put_placeholder()
        self.toolTip.hidetip()
    
    def enterIn(self, *args):
        self.config(bg="yellow")
    
    def clear(self, *args):
        if self["state"] == "disabled":
            return
        self.delete(0, tk.END)
        self.put_placeholder()
        self.toolTip.hidetip()
    
    # 写一个设置禁用状态的方法
    def setDisabled(self, flag : bool):
        if not flag:
            if self.ForceDisabled:
                return
            self["state"] = tk.NORMAL
        else:
            self["state"] = tk.DISABLED
            self.toolTip.hidetip()
    
    # 写一个设置强制禁用状态的方法
    def setForceDisabled(self, flag : bool):
        self.ForceDisabled = flag

class WeatherSysGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("气象数据管理系统")
        self.width = 1154
        self.height = 1000
        self.geometry("{}x{}".format(self.width, self.height))
        self.resizable(False, False)
        self.db = Model()
        self.eng2chs = {"station": "测量站", "place": "地点", "sensor": "传感器", "record": "测量记录"}
        self.page_eng2chs = {"station": "测量站管理", "place": "地点管理", "sensor": "传感器管理", "record": "测量记录管理"}
        self.page_chs2eng = {"测量站管理": "station", "地点管理": "place", "传感器管理": "sensor", "测量记录管理": "record"}
        self.order = ["station", "place", "sensor", "record"]
        self.name_list = ["测量站", "地点", "传感器", "测量记录"]
        self.menu_list = []
        self.page_queue = ["测量站管理"] # 用来记录分页的历史记录（仅记录最近三次）
        self.init_layout()

    def init_layout(self):
        """初始化布局，"""
        # 创建分页控件
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        # 创建分页：测量站管理、地点管理、传感器管理、测量记录管理、联表查询、统计图表
        self.station_page = ttk.Frame(self.notebook)
        self.place_page = ttk.Frame(self.notebook)
        self.sensor_page = ttk.Frame(self.notebook)
        self.record_page = ttk.Frame(self.notebook)
        self.union_search_page = ttk.Frame(self.notebook)
        self.chart_page = ttk.Frame(self.notebook)
        # 将分页添加到分页控件中
        self.notebook.add(self.station_page, text="测量站管理")
        self.notebook.add(self.place_page, text="地点管理")
        self.notebook.add(self.sensor_page, text="传感器管理")
        self.notebook.add(self.record_page, text="测量记录管理")
        self.notebook.add(self.union_search_page, text="联表查询")
        self.notebook.add(self.chart_page, text="统计图表")
        # 初始化表格分页布局
        for table_name in self.order:
            self.init_manage_page_ui(table_name)
        # 初始化联表查询分页布局
        self.init_union_search_page_ui()
        # 初始化统计图表分页布局
        self.init_chart_page_ui()
        # 绑定切换分页事件
        self.notebook.bind("<<NotebookTabChanged>>", self.NotebookTabChanged)
        # 绑定左键单击事件，在全局范围内销毁右键菜单
        self.bind("<Button-1>", lambda event: self.destroy_menu())


    def init_manage_page_ui(self, table_name):
        """初始化分页布局"""
        # 获得分页对象
        page = getattr(self, table_name + "_page")
        # 将分页划分为上下两个部分，上面用来显示记录，下面用来增删查改
        top_frame = tk.Frame(page, height=int(self.height * 0.8),width=self.width)
        setattr(self, table_name + "_page_top", top_frame)
        bottom_frame = tk.Frame(page, height=int(self.height * 0.2),width=self.width)
        setattr(self, table_name + "_page_bottom", bottom_frame)
        # 设置不同的背景色，方便开发时区分
        # top_frame.configure(bg="#ff0000")
        # bottom_frame.configure(bg="#0000ff")
        # 用grid布局
        top_frame.grid(row=0, column=0, sticky=tk.NSEW)
        bottom_frame.grid(row=1, column=0, sticky=tk.NSEW)
        # 固定frame大小
        top_frame.grid_propagate(0)
        bottom_frame.grid_propagate(0)
        # 初始化上下两个部分的布局
        self.init_top_frame_ui(table_name)
        self.init_bottom_frame_ui(table_name)
        # 更新表格
        self.search(table_name)

    def init_top_frame_ui(self, table_name):
        """初始化上半部分布局，包括标题和表格"""
        # 获得上半部分的Frame对象
        top_frame = getattr(self, table_name + "_page_top")
        # 再创建上下两个ttk的frame,分别用来放置标题和表格
        title_frame = ttk.Frame(top_frame,height=int(self.height * 0.05),width=self.width)
        table_frame = ttk.Frame(top_frame,height=int(self.height * 0.75),width=self.width)
        setattr(self, table_name + "_page_top_title_frame", title_frame)
        setattr(self, table_name + "_page_top_table_frame", table_frame)
        # 用grid布局
        title_frame.grid(row=0, column=0, sticky=tk.NSEW)
        table_frame.grid(row=1, column=0, sticky=tk.NSEW)
        # 固定frame大小
        title_frame.grid_propagate(0)
        table_frame.grid_propagate(0)
        # 设置标题，标题为表名的中文，字体大小30，字体为华文新魏，颜色深蓝色，水平竖直居中
        title_label = tk.Label(title_frame, text=self.eng2chs[table_name]+"信息系统", font=("华文新魏", 30, "bold"),fg="navy")
        title_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        # 创建表格控件
        self.create_tree(table_name + "_tree", table_frame)

    def create_tree(self, name : str, table_frame : tk.Frame, do_not_resize : bool = False) -> ttk.Treeview:
        tree = ttk.Treeview(table_frame)
        setattr(self, name, tree)
        # 设置表格显示方式
        tree["show"] = "headings"
        # 设置表格大小，使其完全填充table_frame
        tree.place(relwidth=1, relheight=0.99)
        # 设置表格的垂直滚动条
        scroll_bar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll_bar_y.set)
        scroll_bar_y.place(relx=1, relheight=1, anchor=tk.NE)
        # 设置表格的水平滚动条
        scroll_bar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(xscrollcommand=scroll_bar_x.set)
        scroll_bar_x.place(rely=1, relwidth=1, anchor=tk.SW)
        # 响应鼠标滚轮事件，垂直滚动
        tree.bind("<MouseWheel>", lambda event: tree.yview_scroll(int(-1 * (event.delta / 120)), "units"))
        # 相应<Control-c>事件
        tree.bind('<Control-c>', lambda event: self.copy_cell_value(tree))
        # 相应<Control-a>事件
        tree.bind('<Control-a>', lambda event: self.select_all(tree))
        # 使表头响应鼠标右键点击事件
        tree.bind("<Button-3>", lambda event: self.show_table_menu(tree, event, do_not_resize))
        # 绑定单击事件
        tree.bind("<ButtonRelease-1>", lambda event: self.destroy_menu())

    # 写一个更新表格的方法，用于增删改查后更新表格
    def update_tree(self, tree : ttk.Treeview, headers : list, data : list, do_not_resize : bool = False):
        """更新表格，headers是表头列表，data是二维数据列表"""
        # 先删除原有的数据
        tree.delete(*tree.get_children())
        # 更新表头
        tree["columns"] = headers
        for col in headers:  # 绑定函数，使表头可排序
            tree.heading(col, text=col, command=lambda _col=col: self.treeview_sort_column(tree, _col, False))
        # 用二层循环向表格中添加数据
        for i in range(len(data)):
            tree.insert("", i, values=data[i])
        # 将各列设置为水平居中
        for column in tree["columns"]:
            tree.column(column, anchor=tk.CENTER)
        # 将列宽调整为那一列中最宽的单元格的宽度（自适应列宽）
        if not do_not_resize:
            for i, column in enumerate(headers):
                tree.column(column, width=tkFont.Font().measure(max([column]+[row[i] for row in data], key=lambda x: len(str(x)))))

    def init_bottom_frame_ui(self, table_name):
        """
        初始化下半部分布局，包括输入区域与按钮区域
        输入区域包括三行，一行为字段标题行，一行为由entry组成的输入行，一行为开关行，用来激活或禁用输入行，位置和标题一一对应
        按钮区域包括四个按钮，分别用来增删查改
        """
        # 获得下半部分的Frame对象
        bottom_frame = getattr(self, table_name + "_page_bottom")
        # 再创建上下两个tk的frame,分别用来放置输入区域和按钮区域
        input_frame = tk.Frame(bottom_frame,height=int(self.height * 0.1),width=self.width)
        button_frame = tk.Frame(bottom_frame,height=int(self.height * 0.1),width=self.width)
        # 着色方便区分
        # input_frame.configure(bg="#ff0000")
        # button_frame.configure(bg="#0000ff")
        # 在input_frame和button_frame之间加一条灰色的分割线
        ttk.Separator(bottom_frame, orient=tk.HORIZONTAL).place(relx=0.5, rely=0.5, anchor=tk.CENTER, relwidth=1)
        # 用grid布局
        input_frame.grid(row=0, column=0, sticky=tk.NSEW)
        button_frame.grid(row=1, column=0, sticky=tk.NSEW)
        # 固定frame大小
        input_frame.grid_propagate(0)
        button_frame.grid_propagate(0)
        # 在input_frame中再创建一个input_frame_inner,并在input_frame中水平居中
        input_frame_inner = tk.Frame(input_frame)
        input_frame_inner.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        # 初始化输入区域
        self.init_input_frame(input_frame_inner, table_name)
        # 初始化按钮区域
        self.init_button_frame(button_frame, table_name)

    def init_input_frame(self, input_frame, table_name):
        """初始化输入区域"""
        # 获取表的字段名
        fields = self.db.get_fields(table_name)
        # 获取每个字段标题的文字宽度，并计算所有字段标题文字总宽度，再将每个字段文字宽度除以总宽度，得到每个字段的宽度占比，再乘上窗体宽度，得到每列宽度
        fields_width = [tkFont.Font().measure(field) for field in fields]
        total_width = sum(fields_width)
        # 获取单个文字的宽度，以0的宽度为准，因为entry控件的width的单位是字符数，而不是像素数
        single_width = tkFont.Font().measure("0")
        widths = [int(width / total_width * (self.width / single_width)*1.1) for width in fields_width]
        for i in range(len(fields)):
            # 创建标题行
            field_label = tk.Label(input_frame, text=fields[i], width=widths[i], anchor=tk.CENTER)
            field_label.grid(row=0, column=i, sticky=tk.NSEW)
            # 创建输入行
            entry = tk.Entry(input_frame, width=widths[i])
            entry.grid(row=1, column=i, sticky=tk.NSEW)
            # 绑定<Alt-a>事件，用来全选输入区域
            entry.bind('<Alt-a>', lambda event, e = entry: e.select_range(0, tk.END))
            # 将entry对象保存到self中，方便后续使用
            setattr(self, table_name + "_" + fields[i] + "_entry", entry)
            # 创建开关行，用来激活或禁用输入行，用button来实现
            button = tk.Button(input_frame, height=2,relief=tk.FLAT,command=lambda entry=entry: entry.configure(state=tk.DISABLED if entry["state"] == tk.NORMAL else tk.NORMAL))
            button.grid(row=2, column=i, sticky=tk.NSEW)
            # 当开关行获得焦点时，自动将焦点转移到下一个组件（使得开关行不会获得焦点）
            button.bind("<FocusIn>", lambda event, b=button: b.tk_focusNext().focus_set())


    def init_button_frame(self, button_frame, table_name):
        """初始化按钮区域"""
        # 创建增删查改四个按钮
        insert_button = tk.Button(button_frame, text="增加\n", font=("华文新魏", 20, "bold"), command=lambda: self.insert(table_name), relief=tk.FLAT, anchor=tk.CENTER)
        delete_button = tk.Button(button_frame, text="删除\n", font=("华文新魏", 20, "bold"), command=lambda: self.delete(table_name), relief=tk.FLAT, anchor=tk.CENTER)
        update_button = tk.Button(button_frame, text="修改\n", font=("华文新魏", 20, "bold"), command=lambda: self.updated(table_name), relief=tk.FLAT, anchor=tk.CENTER)
        select_button = tk.Button(button_frame, text="查询\n", font=("华文新魏", 20, "bold"), command=lambda: self.search(table_name), relief=tk.FLAT, anchor=tk.CENTER)
        # 用place水平均匀布局
        insert_button.place(relx=0, rely=0, relwidth=0.25, relheight=1)
        delete_button.place(relx=0.25, rely=0, relwidth=0.25, relheight=1)
        update_button.place(relx=0.5, rely=0, relwidth=0.25, relheight=1)
        select_button.place(relx=0.75, rely=0, relwidth=0.25, relheight=1)
    
    # 清空输入区域
    def clear_input_frame(self, table_name):
        """清空输入区域"""
        fields = self.db.get_fields(table_name)
        for field in fields:
            entry = getattr(self, table_name + "_" + field + "_entry")
            entry.delete(0, tk.END)
    
    def search(self, table_name):
        """查询"""
        # 获取输入区域字段字典，如果entry的值不为空，且未被禁用，则将其加入到字典中
        fields = self.db.get_fields(table_name)
        fields_dict = {}
        for field in fields:
            entry = getattr(self, table_name + "_" + field + "_entry")
            if entry.get() and entry["state"] == tk.NORMAL:
                res = entry.get()
                if "," in res:
                    res = [str_to_num(i) for i in res.split(",")]
                elif "~" in res:
                    res = tuple(str_to_num(i) for i in res.split("~"))
                else:
                    res = str_to_num(res)
                fields_dict[field] = res
        # 查询
        result = self.db.query(table_name, **fields_dict)["data"]
        # 获取表格对象
        tree = getattr(self, table_name + "_tree")
        # 将查询结果显示到表格中
        self.update_tree(tree, fields, result)

    def insert(self, table_name):
        """增加"""
        # 获取输入区域字段字典，如果entry的值不为空，则将其加入到字典中，否则弹窗警告且直接返回
        fields = self.db.get_fields(table_name)
        # 从fields中删去id字段
        fields.remove("id")
        fields_dict = {}
        for field in fields:
            entry = getattr(self, table_name + "_" + field + "_entry")
            if entry.get():
                fields_dict[field] = str_to_num(entry.get())
            else:
                tkMessageBox.showwarning("警告", f"\"{field}\"不能为空")
                return
        # 增加记录，同时处理self.db.ForeignKeyNotExistError异常
        try:
            self.db.insert(table_name, **fields_dict)
        except self.db.ForeignKeyNotExistError as e:
            tkMessageBox.showwarning("引用外键不存在", str(e))
            return
        # 清空输入区域
        self.clear_input_frame(table_name)
        # 调用search方法
        self.search(table_name)
        # 增加后自动选中最后一行
        tree = getattr(self, table_name + "_tree")
        tree.selection_set(tree.get_children()[-1])
        
    def delete(self, table_name):
        """从treeview中拿到所有选中项的id，组成列表，然后删除"""
        # 获取选中项的id
        treeview = getattr(self, table_name + "_tree")
        ids = [treeview.item(item)["values"][0] for item in treeview.selection()]
        # 删除，并捕获DelReferentialIntegrityError异常
        try:
            self.db.delete(table_name, ids)
        except self.db.DelReferentialIntegrityError as e:
            tkMessageBox.showwarning("违反参照完整性", str(e))
            return
        # 清空输入区域
        self.clear_input_frame(table_name)
        # 调用search方法
        self.search(table_name)
    
    def updated(self, table_name):
        """修改"""
        # 获取输入区域字段字典，如果entry的值不为空，则将其加入到字典中，否则弹窗警告且直接返回
        fields = self.db.get_fields(table_name)
        fields.remove("id")
        fields_dict = {}
        for field in fields:
            entry = getattr(self, table_name + "_" + field + "_entry")
            if entry.get():
                fields_dict[field] = str_to_num(entry.get())
        # 获取选中项的id
        treeview = getattr(self, table_name + "_tree")
        ids = [treeview.item(item)["values"][0] for item in treeview.selection()]
        # 修改，并捕获self.db.ForeignKeyNotExistError异常
        for id in ids:
            try:
                self.db.update(table_name, id, **fields_dict)
            except self.db.ForeignKeyNotExistError as e:
                tkMessageBox.showwarning("引用外键不存在", str(e))
                return
        # 清空输入区域
        self.clear_input_frame(table_name)
        # 调用search方法
        self.search(table_name)
        # 修改后自动选中修改的那几行
        ## 遍历每一行，若id在ids中，则选中该行
        for item in treeview.get_children():
            if treeview.item(item)["values"][0] in ids:
                treeview.selection_add(item)



    def init_union_search_page_ui(self):
        """初始化联表查询UI"""
        page = self.union_search_page
        # 创建上中下三层frame
        title_frame = tk.Frame(page, height=int(self.height * 0.05),width=self.width)
        result_frame = tk.Frame(page, height=int(self.height * 0.45),width=self.width)
        input_frame = tk.Frame(page, height=int(self.height * 0.5),width=self.width)
        # 使用grid布局
        title_frame.grid(row=0, column=0, sticky=tk.NSEW)
        result_frame.grid(row=1, column=0, sticky=tk.NSEW)
        input_frame.grid(row=2, column=0, sticky=tk.NSEW)
        # 固定三个frame的大小
        title_frame.grid_propagate(0)
        result_frame.grid_propagate(0)
        input_frame.grid_propagate(0)
        # 给三个frame添加背景色，方便观察
        # title_frame["bg"] = "red"
        # result_frame["bg"] = "green"
        # input_frame["bg"] = "blue"
        # 设置标题，字体大小30，字体为华文新魏，颜色深蓝色，水平竖直居中
        title_label = tk.Label(title_frame, text="联表查询", font=("华文新魏", 30))
        title_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        # 创建表格
        self.create_tree("union_search_result_table", result_frame, True)
        # 在input_frame中创建四个frame，分别用于放置四个表的查询条件，并在之间加入分割线
        table_names = self.order
        for i in range(4):
            table_name = table_names[::-1][i]
            inner_frame = tk.Frame(input_frame,height=int(self.height * 0.1),width=self.width)
            setattr(self, table_name + "_union_search_input_frame", inner_frame)
            inner_frame.grid(row=i, column=0, sticky=tk.NSEW)
            # 固定大小
            inner_frame.grid_propagate(0)
            # 加入分割线
            separator = ttk.Separator(input_frame, orient=tk.HORIZONTAL)
            separator.place(relx=0.5, rely=(i + 1) * 0.2, relwidth=1, anchor=tk.CENTER)
            # 在inner_frame中左右创建两个frame，分别用来放置按钮和输入框
            left_frame = tk.Frame(inner_frame,height=int(self.height * 0.1),width=int(self.width * 0.2))
            right_frame = tk.Frame(inner_frame,height=int(self.height * 0.1),width=int(self.width * 0.8))
            setattr(self, table_name + "_union_search_input_frame", right_frame)
            left_frame.grid(row=0, column=0, sticky=tk.NSEW)
            right_frame.grid(row=0, column=1, sticky=tk.NSEW)
            # 固定大小
            left_frame.grid_propagate(0)
            right_frame.grid_propagate(0)
            # 在left_frame与right_frame之间加入分割线
            separator = ttk.Separator(inner_frame, orient=tk.VERTICAL)
            separator.place(relx=0.2, rely=0.5, relheight=1, anchor=tk.CENTER)
            # 在left_frame中创建按钮
            button = tk.Button(left_frame, text=self.eng2chs[table_name], relief=tk.FLAT, font=("华文新魏", 35), 
                               activeforeground="navy")
            button.config(command=lambda table_name=table_name, button=button: self.union_input_button_click(table_name,button,False))
            # 给button绑定右键事件
            button.bind("<Button-3>", lambda event, table_name=table_name, button=button : self.union_input_button_right_click(table_name, button))
            setattr(self, table_name + "_union_search_button", button)
            # button布满整个left_frame
            button.place(relx=0, rely=0, relwidth=1, relheight=1)
            # 创建right_frame的组件列表
            input_widgets = dict()
            setattr(self, table_name + "_union_search_input_widgets", input_widgets)
            # 获取字段列表
            fields = self.db.get_fields(table_name)
            # 从字段列表中去除id字段
            # fields.remove("id")
            # 遍历字段，往right_frame中添加PlaceholderEntry，用grid布局，并把PlaceholderEntry添加到input_widgets中
            for i, field in enumerate(fields):
                # 创建PlaceholderEntry
                entry = PlaceholderEntry(right_frame, placeholder=field, font=(50),width=25)
                # 添加到input_widgets中
                input_widgets[field] = entry
                # 使用grid布局，当一行放不下时，自动换行
                entry.grid(row=i // 4, column=i % 4, sticky=tk.NSEW,ipady=10)
                # 给entry绑定右键事件
                entry.bind("<Button-3>", lambda event, entry=entry: entry.setDisabled(entry["state"] != tk.DISABLED))
        # 在底部再创建一个frame，用来放置查询按钮和清空按钮
        bottom_frame = tk.Frame(input_frame,height=int(self.height * 0.1),width=self.width)
        bottom_frame.grid(row=4, column=0, sticky=tk.NSEW)
        # 固定大小
        bottom_frame.grid_propagate(0)
        # 在bottom_frame中创建两个按钮
        search_button = tk.Button(bottom_frame, text="查询\n", relief=tk.FLAT, font=("华文新魏", 20))
        self.union_search_button = search_button
        clear_button = tk.Button(bottom_frame, text="清空\n", relief=tk.FLAT, font=("华文新魏", 20), command=self.clear_union_search_input)
        # 按钮布满整个bottom_frame
        clear_button.place(relx=0, rely=0, relwidth=0.5, relheight=1)
        search_button.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)

    def clear_union_search_input(self):
        """清空联表查询输入框"""
        # 获取所有输入框
        for name in self.order:
            input_widgets = getattr(self, name + "_union_search_input_widgets")
            for widget in input_widgets.values():
                widget.clear()

    def union_input_button_click(self, table_name, button, state : bool):
        """联表查询输入按钮点击事件"""
        # 切换输入框状态
        self.toggle_union_search_input_entry(table_name, state)
        # 重新绑定点击事件为相反状态
        button.config(command=lambda table_name=table_name, button=button: self.union_input_button_click(table_name,button,not state))

    def union_input_button_right_click(self, table_name, button):
        """联表查询输入按钮右键事件，用来自动到table_name表中选中"""
        # 若button已被禁用，则不执行
        if button["state"] == tk.DISABLED:
            return
        # 获得分页名称
        page_name = self.page_eng2chs[table_name]
        # 切换分页
        self.changeTab(page_name)
        # 获得联表的treeview
        treeview = getattr(self, "union_search_result_table")
        # 变换字段
        if table_name == self.page_chs2eng[self.page_queue[1]]:
            zd = "id"
        else:
            zd = self.eng2chs[table_name] + "ID"
        i = treeview["columns"].index(zd)
        # 获得值
        ids = [str(treeview.item(item)["values"][i]) for item in treeview.selection()]
        # ids去重
        ids = list(set(ids))
        # 拼接查询语句
        search_str = ",".join(ids)
        # 拿到entry对象
        entry = getattr(self, table_name + "_" + "id" + "_entry")
        # 清空输入框
        self.clear_input_frame(table_name)
        # 插入查询语句
        entry.insert(0, search_str)
        # 调用查询方法
        self.search(table_name)
        # 禁用输入框
        entry["state"] = tk.DISABLED
        # 获得对应表tree
        tree = getattr(self, table_name + "_tree")
        # 全选
        tree.selection_set(tree.get_children())

    def toggle_union_search_input_entry(self, table_name, state : bool):
        """切换对应表的输入区域的输入框状态"""
        input_widgets = getattr(self, table_name + "_union_search_input_widgets")
        for widget in input_widgets.values():
            widget.setForceDisabled(not state)
            widget.setDisabled(not state)

    def toggle_union_search_input_button(self, table_name, state : bool):
        """切换对应表的输入区域的按钮状态"""
        button = getattr(self, table_name + "_union_search_button")
        button["state"] = tk.NORMAL if state else tk.DISABLED
    
    def update_union_search_ui(self, table_name):
        """更新联表查询界面"""
        # 先禁用所有输入区域
        for name in self.order:
            self.toggle_union_search_input_entry(name, False)
            self.toggle_union_search_input_button(name, False)
        # 再对order表从table_name开始向前启用
        index = self.order.index(table_name)
        for i in range(index, -1, -1):
            name = self.order[i]
            self.toggle_union_search_input_entry(name, True)
            self.toggle_union_search_input_button(name, True)
            # 获取对应输入区域组件表
            input_widgets = getattr(self, name + "_union_search_input_widgets")
            if i != index:
                # 将第一个组件隐藏
                input_widgets["id"].grid_remove()
            else:
                # 将第一个组件显示
                input_widgets["id"].grid()
        # 重新绑定查询按钮事件
        self.union_search_button.config(command=lambda table_name=table_name: self.union_search(table_name))

    def union_search(self, table_name):
        """联表查询"""
        # 获取输入框组件表
        input_widgets = []
        for name in self.order:
            right_frame = getattr(self, name + "_union_search_input_frame")
            visible_normal_widgets = []
            for widget in right_frame.winfo_children():
                if widget.winfo_ismapped() and widget["state"] == tk.NORMAL:
                    visible_normal_widgets.append(widget)
            input_widgets.append(visible_normal_widgets)
        # 构造字典，key是widget的placeholder，value是widget的值，若value为空，则不添加到字典中
        input_dict = dict()
        for i, widgets in enumerate(input_widgets):
            for widget in widgets:
                res = widget.get()
                if res:
                    if "," in res:
                        res = [str_to_num(i) for i in res.split(",")]
                    elif "~" in res:
                        res = tuple(str_to_num(i) for i in res.split("~"))
                    else:
                        res = str_to_num(res)
                    input_dict[widget.placeholder] = res
        # 调用model的联表查询方法
        result = self.db.union_query(table_name, **input_dict)
        # 更新表格
        self.update_tree(getattr(self,"union_search_result_table"),result["columns"],result["data"],do_not_resize=True)

    def init_chart_page_ui(self):
        """将matplotlib绘制的图表显示到界面上"""
        # 创建画布
        self.fig = Figure(figsize=(10, 8), dpi=100)
        # 创建子图
        self.ax = self.fig.add_subplot(111)
        # 创建绘图区域
        self.canvas = FigureCanvasTkAgg(self.fig, self.chart_page)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        # 创建工具栏
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.chart_page)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(fill=tk.BOTH, expand=True)

    def draw_record_line(self, event):
        """获取被选中的测量记录数据,调用refresh_chart绘制折线图"""
        treeview = getattr(self, "record_tree")
        # 获取被选中的记录的时间
        datetimes = [treeview.item(item)["values"][1] for item in treeview.selection()]
        # 获取被选中的记录的测量值
        values = [float(treeview.item(item)["values"][2]) for item in treeview.selection()]
        # 调用refresh_chart绘制折线图
        self.refresh_chart((datetimes, values), "time", "measure_value")
        
    def refresh_chart(self, data, x : str, y : str):
        """更新折线图,其中data是列表元组,元组中有两个列表,分别代表x的值和y的值"""
        # 清空子图
        self.ax.clear()
        # 绘制折线图
        self.ax.plot(data[0], data[1])
        # 设置标签
        self.ax.set_xlabel(x)
        self.ax.set_ylabel(y)
        
        # 获取y轴的最大值和最小值
        y_max = max(data[1])
        y_min = min(data[1])
        # 设置y轴的刻度
        self.ax.set_yticks(np.linspace(y_min, y_max, 10))
        
        # 解决中文乱码问题
        # self.ax.set_xlabel(x, fontproperties=font)
        # self.ax.set_ylabel(y, fontproperties=font)
        # 绘制图形
        self.canvas.draw()

# 响应快捷键

    def copy_cell_value(self, tree : ttk.Treeview):
        """弹出一个选择复制单元格的窗口"""
        # 获取选中行
        selected_items = tree.selection()
        # 判断是否大于一行
        if len(selected_items) > 1:
            tkMessageBox.showwarning("警告", "只能选择一个单元格")
            # 清除选中状态
            tree.selection_remove(selected_items)
            return
        # 获取选中行的值列表
        values = [str(s) for s in tree.item(selected_items[0])["values"]]
        allow_copy_window = tk.Toplevel(self)
        # 根据values列表在一行内创建多个按钮，每个按钮的标签为value的值，宽度为value的文本宽度
        btn_list = []
        for i, value in enumerate(values):
            btn = tk.Button(allow_copy_window,text=value, width=len(value)+4, command=lambda v=value: self.copy_value(v, allow_copy_window), relief=tk.FLAT)
            btn_list.append(btn)
            # 使用pack横向排列
            btn.pack(side=tk.LEFT)
        allow_copy_window.title("请选择复制内容")
        # 设置窗口大小，高度只有一个按钮高度，宽度为所有按钮宽度之和
        allow_copy_window.geometry(f"{sum([btn.winfo_reqwidth() for btn in btn_list])}x{btn_list[0].winfo_reqheight()}")
        allow_copy_window.resizable(False, False)

    def copy_value(self, value, window):
        """复制value的值到剪贴板，并关闭窗口"""
        clipboard.copy(value)
        window.destroy()

    def select_all(self, tree : ttk.Treeview):
        """选中所有行"""
        tree.selection_set(tree.get_children())

    def treeview_sort_column(self, tv, col, reverse):  # Treeview、列名、排列方式
        """按列排序函数"""
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(reverse=reverse, key=lambda x: str_to_num(x[0]))  # 排序方式
        # rearrange items in sorted positions
        for index, (val, k) in enumerate(l):  # 根据排序后索引移动
            tv.move(k, '', index)
        tv.heading(col, command=lambda: self.treeview_sort_column(tv, col, not reverse))  # 重写标题，使之成为再点倒序的标题

    def destroy_menu(self):
        """销毁所有菜单"""
        for menu in self.menu_list:
            menu.destroy()
        self.menu_list.clear()

    def show_table_menu(self, tree : ttk.Treeview, event, do_not_resize : bool = False):
        """显示表格右键菜单"""
        # 先销毁其他菜单
        self.destroy_menu()
        # 获取鼠标位置
        x, y = event.x_root, event.y_root
        # 创建菜单
        menu = tk.Menu(self, tearoff=0)
        ## 添加子菜单
        sub_menu = tk.Menu(menu, tearoff=0)
        self.menu_list.append(menu)
        self.menu_list.append(sub_menu)
        # 添加菜单项
        menu.add_cascade(label="显示/隐藏列", menu=sub_menu)
        menu.add_command(label="复制单元格", command=lambda: self.copy_cell_value(tree))
        menu.add_command(label="全选", command=lambda: self.select_all(tree))
        menu.add_command(label="关闭菜单", command=lambda: self.destroy_menu())
        # 获取tree的columns与displaycolumns
        columns = tree["columns"]
        displaycolumns = tree["displaycolumns"]
        if displaycolumns[0] == "#all":
            displaycolumns = columns
        # 遍历columns，将column添加到子菜单的菜单项中
        for column in columns:
            # 判断column是否在displaycolumns中，在column前加上*号
            if column in displaycolumns:
                label = "*  " + column
                # 添加菜单项，并绑定事件，点击后隐藏column
                sub_menu.add_command(label=label, command=lambda c=column: self.hide_column(tree, c, do_not_resize))
            else:
                label = "   "+ column
                # 添加菜单项，并绑定事件，点击后显示column
                sub_menu.add_command(label=label, command=lambda c=column: self.show_column(tree, c, do_not_resize))

        # 显示菜单
        menu.post(x, y)
    
    def hide_column(self, tree : ttk.Treeview, column : str, do_not_resize : bool = False):
        """隐藏column列"""
        columns = tree["columns"]
        displaycolumns = tree["displaycolumns"]
        if displaycolumns[0] == "#all":
            displaycolumns = columns
        # 重新构造displaycolumns
        displaycolumns = tuple(c for c in displaycolumns if c != column)
        # 设置tree的displaycolumns
        tree["displaycolumns"] = displaycolumns
        # 将列宽调整为那一列中最宽的单元格的宽度（自适应列宽）
        if not do_not_resize:
            headers, data = self.get_treeview_data(tree)
            for i, column in enumerate(columns):
                tree.column(column, width=tkFont.Font().measure(max([column]+[row[i] for row in data], key=lambda x: len(str(x)))))


    def show_column(self, tree : ttk.Treeview, column : str, do_not_resize : bool = False):
        """显示column列"""
        columns = tree["columns"]
        displaycolumns = tree["displaycolumns"]
        # 重新构造displaycolumns
        new_displaycolumns = []
        for c in columns:
            if c == column or c in displaycolumns:
                new_displaycolumns.append(c)
        new_displaycolumns = tuple(new_displaycolumns)
        headers, data = self.get_treeview_data(tree)
        if new_displaycolumns == columns:
            new_displaycolumns = ("#all",)
            headers = columns
        # 设置tree的displaycolumns
        tree["displaycolumns"] = new_displaycolumns
        # 将列宽调整为那一列中最宽的单元格的宽度（自适应列宽）
        if not do_not_resize:
            for i, column in enumerate(headers):
                tree.column(column, width=tkFont.Font().measure(max([column]+[row[i] for row in data], key=lambda x: len(str(x)))))

    def get_treeview_data(self, tree : ttk.Treeview):
        """获取columns与二维列表data"""
        # 获取columns
        columns = tree["columns"]
        # 获取data
        data = []
        for item in tree.get_children():
            values = [tree.set(item, column) for column in columns]
            data.append(values)
        return columns, data

    def NotebookTabChanged(self, event):
        """Notebook页改变事件"""
        # 获取当前页
        current_tab = event.widget.tab(event.widget.select(), "text")
        # 将current_tab添加到self.page_list队列中
        self.page_queue.append(current_tab)
        # 如果self.page_queue的长度大于3，则删除第一个元素
        if len(self.page_queue) > 3:
            self.page_queue.pop(0)
        last_tab = self.page_queue[1]
        # 判断current_tab是否为联表查询
        if current_tab == "联表查询":
            # 更新联表查询ui
            self.update_union_search_ui(self.page_chs2eng[last_tab])

    def changeTab(self, tab_name : str):
        """切换到tab_name页"""
        # 先获得所有页的名称
        tabs = [self.notebook.tab(i, "text") for i in range(self.notebook.index("end"))]
        # 判断tab_name是否在tabs中
        if tab_name in tabs:
            # 切换到tab_name页
            self.notebook.select(tabs.index(tab_name))
        else:
            # 直接返回
            return

if __name__ == "__main__":
    # 给表添加测试数据
    data_dir = os.path.join(current_path, "data")
    # 如果数据文件不存在，就添加记录
    import random, string
    if not os.path.exists(data_dir):
        db = Model()
        for i in range(40):
            station_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            db.insert("station", 测量站名称=station_name, 代表地区="南京信息工程大学", 测量站状态="上线")
            place_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            db.insert("place", 地点编号=place_id, 经度=random.uniform(118.0, 119.0), 纬度=random.uniform(31.0, 33.0), 海拔=random.uniform(0, 1000), 地点状态="上线", 测量站ID=0)
            sensor_type = random.choice(["温度传感器", "湿度传感器", "气压传感器"])
            sensor_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            db.insert("sensor", 传感器类型=sensor_type, 测量值单位=random.choice(["℃", "%", "kPa"]), 传感器编号=sensor_id, 上线时间="2023-06-05", 下线时间="2027-06-05", 传感器状态="上线", 地点ID=0)
            db.insert("record", 时间="2023-06-05 12:00:00", 测量值=random.uniform(20, 30), 传感器ID=0)
            db.insert("record", 时间="2023-06-05 13:00:00", 测量值=random.uniform(20, 30), 传感器ID=0)
            db.insert("record", 时间="2023-06-05 14:00:00", 测量值=random.uniform(20, 30), 传感器ID=0)
            db.insert("record", 时间="2023-06-05 15:00:00", 测量值=random.uniform(20, 30), 传感器ID=0)

    app = WeatherSysGUI()
    app.mainloop()
