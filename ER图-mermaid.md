# 教学效果监督系统 E-R 图（Mermaid 版）

下面这段可以直接复制到支持 Mermaid 的编辑器里渲染。

```mermaid
erDiagram
    USERS {
        int id PK
        string username UK
        string password_hash
        string name
        string email UK
        string role
        datetime created_at
        boolean is_active
    }

    COURSES {
        int id PK
        string name
        string code UK
        text description
        string semester
        int teacher_id FK
        datetime created_at
        boolean is_active
    }

    CLASSES {
        int id PK
        string name
        int course_id FK
        int student_count
        datetime created_at
    }

    STUDENTS {
        int id PK
        string student_no UK
        string name
        string gender
        int class_id FK
        datetime created_at
    }

    ATTENDANCES {
        int id PK
        int student_id FK
        date date
        string status
        int course_id FK
        string remark
        datetime created_at
    }

    HOMEWORKS {
        int id PK
        int student_id FK
        string title
        float score
        float max_score
        datetime submit_time
        datetime deadline
        string status
        int course_id FK
        datetime created_at
    }

    QUIZZES {
        int id PK
        int student_id FK
        string title
        float score
        float max_score
        int duration
        datetime submit_time
        int course_id FK
        datetime created_at
    }

    INTERACTIONS {
        int id PK
        int student_id FK
        string type
        int count
        date date
        int course_id FK
        datetime created_at
    }

    WARNINGS {
        int id PK
        int student_id FK
        int course_id FK
        string type
        string level
        text reason
        json metrics
        text suggestion
        string status
        int handled_by FK
        datetime handled_at
        text handle_note
        datetime created_at
    }

    USERS ||--o{ COURSES : "teaches"
    COURSES ||--o{ CLASSES : "contains"
    CLASSES ||--o{ STUDENTS : "has"

    STUDENTS ||--o{ ATTENDANCES : "has"
    STUDENTS ||--o{ HOMEWORKS : "has"
    STUDENTS ||--o{ QUIZZES : "has"
    STUDENTS ||--o{ INTERACTIONS : "has"
    STUDENTS ||--o{ WARNINGS : "triggers"

    COURSES ||--o{ ATTENDANCES : "records"
    COURSES ||--o{ HOMEWORKS : "assigns"
    COURSES ||--o{ QUIZZES : "contains"
    COURSES ||--o{ INTERACTIONS : "tracks"
    COURSES ||--o{ WARNINGS : "owns"

    USERS ||--o{ WARNINGS : "handles"
```

## 论文里建议怎么放

图名建议直接写：`图4.5 数据库 E-R 图`

图下注释可以用这句：

`图4.5 展示了教学效果监督系统的核心实体及关系，其中课程、班级、学生构成基础教学组织结构，考勤、作业、测验、互动和预警记录围绕学生与课程展开。`

## 如果 Mermaid 渲染不出来

你可以直接照这个结构在 ProcessOn 或 draw.io 里手动画：

1. 最上方放 `USERS`
2. 第二层放 `COURSES`
3. 第三层放 `CLASSES`
4. 第四层放 `STUDENTS`
5. `STUDENTS` 右侧竖着排 `ATTENDANCES / HOMEWORKS / QUIZZES / INTERACTIONS / WARNINGS`
6. 再从 `COURSES` 分别连到这 5 张业务表
7. 从 `USERS` 再连一条到 `WARNINGS.handled_by`

这样布局最清楚，也最适合论文截图。
