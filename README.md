# WeatherInfoSys
气象数据管理系统
# 模型设计
## 数据原型
### 测量站表

| 字段名 | 数据类型 |
| ------ | -------- |
| id | int |
| 测量站名称 | varchar |
| 代表地区 | varchar |
| 测量站状态 | varchar |

### 地点表

| 字段名 | 数据类型 |
| ------ | -------- |
| id | int |
| 地点编号 | varchar |
| 经度 | float |
| 纬度 | float |
| 海拔 | float |
| 地点状态 | varchar |
| 测量站ID | int |

### 传感器表

| 字段名 | 数据类型 |
| ------ | -------- |
| id | int |
| 传感器类型 | varchar |
| 测量值单位 | varchar |
| 传感器编号 | varchar |
| 上线时间 | datetime |
| 下线时间 | datetime |
| 传感器状态 | varchar |
| 地点ID | int |

### 测量记录表

| 字段名 | 数据类型 |
| ------ | -------- |
| id | int |
| 时间 | datetime |
| 测量值 | float |
| 传感器ID | int |
