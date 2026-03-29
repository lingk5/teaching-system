# 权重公式统一优化设计文档

## 📋 项目信息
- **项目名称**: teaching-system 教学效果监督系统
- **设计主题**: 权重公式统一化
- **设计日期**: 2026-03-28
- **设计者**: 小智 (AI Assistant)
- **审核者**: 子木 (老板)

---

## 🎯 设计目标

### 当前问题
项目存在三套不同的权重公式，导致数据统计口径不一致：
1. **预警引擎**: 使用 `30%出勤 + 30%作业 + 30%测验 + 10%互动`
2. **导出报表**: 疑似使用 `30%出勤 + 30%作业 + 40%测验`（未确认互动）
3. **前端说明**: 未明确公式，可能不一致

### 设计目标
1. **统一所有模块的权重公式**
2. **建立集中化的权重配置**
3. **确保数据统计一致性**
4. **保持向后兼容性**

### 成功标准
- ✅ 所有模块使用相同的权重配置
- ✅ 导出报表计算结果与预警引擎一致
- ✅ 前端公式说明与实现匹配
- ✅ 现有功能不受影响

---

## 🔍 现状分析

### 1. 预警引擎权重配置
**文件**: `backend/app/services/warning_engine.py`
```python
WEIGHTS = {
    'attendance': 0.3,      # 30%
    'homework': 0.3,        # 30%
    'quiz': 0.3,           # 30%
    'interaction': 0.1     # 10%
}
```

### 2. 导出模块权重使用
**需要调查的文件**: `backend/app/routes/export.py`
**预期问题**: 导出报表可能使用不同的权重分配

### 3. 前端公式说明
**需要检查的文件**: `frontend/src/pages/analytics.html` 等
**预期问题**: 前端可能显示不准确的公式说明

### 4. 数据分析接口
**文件**: `backend/app/routes/analytics.py`
**预期问题**: 分析接口可能使用不一致的计算方式

---

## 📊 设计方案

### 方案选择：集中化权重配置

#### 方案A：常量模块配置（推荐）
在`backend/app/services/`下创建权重配置常量模块。

**优点**：
- 集中管理，一处修改全局生效
- 易于维护和测试
- 类型安全，可添加文档

**缺点**：
- 需要修改多个导入点

#### 方案B：配置文件
将权重配置到`.env`或配置文件中。

**优点**：
- 可动态调整权重
- 无需重新部署修改

**缺点**：
- 配置复杂化
- 需要添加配置解析逻辑

#### 方案C：数据库配置
将权重存储到数据库中。

**优点**：
- 支持运行时调整
- 可记录历史配置

**缺点**：
- 过度设计，增加复杂度
- 需要管理界面

**推荐方案**: **方案A** - 适合当前项目规模，简单高效。

---

## 🛠️ 详细设计

### 1. 创建权重配置模块
**文件**: `backend/app/services/weight_config.py`

```python
"""
权重配置模块 - 统一管理系统中所有计算公式的权重
"""


class WeightConfig:
    """权重配置类，提供统一的权重定义和验证"""
    
    # ================== 综合评分权重 ==================
    # 综合评分 = attendance*30% + homework*30% + quiz*30% + interaction*10%
    COMPREHENSIVE_WEIGHTS = {
        'attendance': 0.3,      # 出勤权重 30%
        'homework': 0.3,        # 作业权重 30%
        'quiz': 0.3,           # 测验权重 30%
        'interaction': 0.1     # 互动权重 10%
    }
    
    # 权重验证：总和必须为1.0
    COMPREHENSIVE_TOTAL = sum(COMPREHENSIVE_WEIGHTS.values())  # 应为1.0
    
    # ================== 阈值配置 ==================
    WARNING_THRESHOLDS = {
        'red': 60,     # 红色预警：<60分
        'orange': 75,  # 橙色预警：60-75分
        'yellow': 85   # 黄色预警：75-85分
    }
    
    # ================== 权重计算工具方法 ==================
    @classmethod
    def calculate_comprehensive_score(cls, metrics):
        """
        计算综合评分
        :param metrics: 字典，包含各项指标的得分 (0-100)
        :return: 综合评分 (0-100)
        """
        score = 0
        for key, weight in cls.COMPREHENSIVE_WEIGHTS.items():
            if key in metrics:
                score += metrics[key] * weight
            else:
                raise ValueError(f"缺少必要的指标: {key}")
        
        # 确保分数在合理范围内
        return max(0, min(100, score))
    
    @classmethod
    def get_weight_description(cls):
        """获取权重描述的文本"""
        return (
            "综合评分 = "
            f"出勤({cls.COMPREHENSIVE_WEIGHTS['attendance']*100:.0f}%) + "
            f"作业({cls.COMPREHENSIVE_WEIGHTS['homework']*100:.0f}%) + "
            f"测验({cls.COMPREHENSIVE_WEIGHTS['quiz']*100:.0f}%) + "
            f"互动({cls.COMPREHENSIVE_WEIGHTS['interaction']*100:.0f}%)"
        )
    
    @classmethod
    def get_warning_level(cls, score):
        """根据分数获取预警等级"""
        if score < cls.WARNING_THRESHOLDS['red']:
            return 'red'
        if score < cls.WARNING_THRESHOLDS['orange']:
            return 'orange'
        if score < cls.WARNING_THRESHOLDS['yellow']:
            return 'yellow'
        return None
```

### 2. 修改预警引擎
**文件**: `backend/app/services/warning_engine.py`

修改点：
1. 导入`WeightConfig`模块
2. 移除内部的`WEIGHTS`和`THRESHOLDS`常量
3. 使用`WeightConfig`的计算方法

```python
from ..services.weight_config import WeightConfig

class WarningEngine:
    # 移除原有的 WEIGHTS 和 THRESHOLDS 定义
    
    def _calculate_comprehensive_score(self, metrics):
        """使用统一的权重配置计算综合分"""
        return WeightConfig.calculate_comprehensive_score(metrics)
    
    def _determine_warning_level(self, score):
        """使用统一的阈值判断预警等级"""
        return WeightConfig.get_warning_level(score)
```

### 3. 修改导出模块
**文件**: `backend/app/routes/export.py`

需要检查导出模块中成绩计算的部分，确保使用相同的权重公式：

```python
# 如果导出模块有独立的成绩计算，需要修改为：
from ..services.weight_config import WeightConfig

# 在计算综合成绩的地方使用：
metrics = {
    'attendance': attendance_score,
    'homework': homework_score,
    'quiz': quiz_score,
    'interaction': interaction_score
}
comprehensive_score = WeightConfig.calculate_comprehensive_score(metrics)
```

### 4. 添加前端公式说明
**文件**: `frontend/src/pages/analytics.html` 或其他相关页面

在合适的位置添加公式说明：
```html
<!-- 在学情分析页面添加公式说明 -->
<div class="alert alert-info">
    <strong>综合评分计算公式：</strong>
    出勤(30%) + 作业(30%) + 测验(30%) + 互动(10%)
</div>
```

或者通过API动态获取：
```javascript
// 可以添加API返回公式描述
async function loadWeightInfo() {
    const response = await request.get('/api/config/weights');
    const weightInfo = response.data;
    document.getElementById('formulaDisplay').innerText = weightInfo.description;
}
```

### 5. 创建权重信息API（可选）
**文件**: `backend/app/routes/config.py`（新创建）

```python
from flask import Blueprint, jsonify
from ..services.weight_config import WeightConfig

config_bp = Blueprint('config', __name__)

@config_bp.route('/weights', methods=['GET'])
def get_weight_config():
    """获取权重配置信息"""
    return jsonify({
        'success': True,
        'data': {
            'weights': WeightConfig.COMPREHENSIVE_WEIGHTS,
            'thresholds': WeightConfig.WARNING_THRESHOLDS,
            'description': WeightConfig.get_weight_description(),
            'total_weight': WeightConfig.COMPREHENSIVE_TOTAL
        }
    })
```

---

## 🔄 实施步骤

### 阶段一：分析确认 (预计：0.5天)
1. 彻底分析导出模块的实际权重使用
2. 确认前端哪些位置需要公式说明
3. 检查所有涉及成绩计算的位置

### 阶段二：核心实现 (预计：1天)
1. 创建`weight_config.py`模块
2. 修改预警引擎使用新配置
3. 修改导出模块使用新配置

### 阶段三：前端更新 (预计：0.5天)
1. 添加公式说明到前端页面
2. 可选：创建权重信息API和前端调用

### 阶段四：测试验证 (预计：1天)
1. 单元测试：验证权重计算正确性
2. 集成测试：验证导出与预警计算结果一致
3. 回归测试：确保现有功能不受影响

---

## 🧪 测试计划

### 1. 单元测试
**文件**: `backend/tests/test_weight_config.py`

```python
import unittest
from app.services.weight_config import WeightConfig

class TestWeightConfig(unittest.TestCase):
    def test_weight_sum(self):
        """测试权重总和是否为1.0"""
        self.assertEqual(WeightConfig.COMPREHENSIVE_TOTAL, 1.0)
    
    def test_calculate_score(self):
        """测试综合评分计算"""
        metrics = {
            'attendance': 80,
            'homework': 70,
            'quiz': 90,
            'interaction': 60
        }
        expected = 80*0.3 + 70*0.3 + 90*0.3 + 60*0.1
        actual = WeightConfig.calculate_comprehensive_score(metrics)
        self.assertEqual(expected, actual)
    
    def test_warning_level(self):
        """测试预警等级判断"""
        self.assertEqual(WeightConfig.get_warning_level(55), 'red')
        self.assertEqual(WeightConfig.get_warning_level(70), 'orange')
        self.assertEqual(WeightConfig.get_warning_level(80), 'yellow')
        self.assertIsNone(WeightConfig.get_warning_level(90))
```

### 2. 集成测试
1. **预警与导出一致性测试**：
   - 选择若干学生数据
   - 分别通过预警引擎和导出模块计算综合分
   - 验证两个结果是否一致

2. **前后端一致性测试**：
   - 通过API获取权重配置
   - 验证前端显示的公式与后端配置一致

### 3. 回归测试清单
- [ ] 预警生成功能正常
- [ ] 预警等级判断正确
- [ ] 导出报表功能正常
- [ ] 导出成绩计算正确
- [ ] 学情分析页面正常
- [ ] 仪表盘数据正确

---

## ⚠️ 风险与应对

### 风险1：导出模块权重逻辑复杂
**可能性**: 中
**影响**: 修改困难，可能破坏现有导出功能
**应对**：
1. 先彻底分析导出模块逻辑
2. 编写测试用例验证现有功能
3. 逐步重构，确保每一步都有测试

### 风险2：前端公式位置不明确
**可能性**: 低
**影响**: 用户可能看不到公式说明
**应对**：
1. 仔细检查前端所有涉及评分的位置
2. 在关键位置（学情分析、预警详情）添加说明
3. 使用工具提示等方式提升可发现性

### 风险3：权重配置影响现有数据
**可能性**: 低
**影响**: 修改权重后历史预警等级可能变化
**应对**：
1. 保持权重不变（30/30/30/10）
2. 说明这是修复而非修改
3. 如有必要，可添加历史数据迁移

---

## 📈 成功指标

### 量化指标
1. **代码一致性**: 100%模块使用相同的权重配置
2. **计算一致性**: 预警引擎与导出计算结果差异 < 0.01
3. **测试覆盖率**: 权重相关代码覆盖率 > 90%

### 质量指标
1. **可维护性**: 权重修改只需修改一处
2. **可读性**: 权重配置有清晰的文档说明
3. **可测试性**: 所有权重计算有单元测试

---

## 🚀 后续计划

完成权重统一后，可考虑以下优化：

### 1. 权重可配置化
将权重配置移至数据库，支持教师自定义权重。

### 2. 权重版本管理
支持不同学期使用不同权重，保留历史配置。

### 3. 权重影响分析
分析不同权重配置对预警结果的影响，提供优化建议。

---

## 📝 审批与执行

**设计评审通过后，将按以下步骤执行**：

1. ✅ **设计文档创建** (已完成)
2. 🔄 **老板审核批准** (等待中)
3. ⏳ **实施计划细化**
4. ⏳ **代码实现**
5. ⏳ **测试验证**
6. ⏳ **部署上线**

---

**设计文档完成时间**: 2026-03-28 16:43  
**预计总工时**: 3天  
**影响范围**: 中（核心业务模块）  
**风险评估**: 中低（保持现有权重不变）

---
*文档版本: v1.0*
*最后更新: 2026-03-28*