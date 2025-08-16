# 第7章：查询优化与性能调优

## 本章概述

查询优化与性能调优是 SQLModel 应用开发中的关键环节。本章将深入探讨如何编写高效的查询语句、优化数据库性能、监控查询执行情况，以及解决常见的性能瓶颈问题。

### 学习目标

通过本章学习，你将能够：
- 理解查询执行原理和性能影响因素
- 掌握查询优化的基本技巧和高级策略
- 学会使用索引优化查询性能
- 实现有效的缓存策略
- 监控和分析查询性能
- 解决常见的性能问题

### 本章结构

1. **查询执行原理** - 理解 SQL 查询的执行过程
2. **基础查询优化** - 掌握基本的查询优化技巧
3. **索引策略** - 学习索引的设计和使用
4. **高级优化技术** - 探索高级的性能优化方法
5. **缓存策略** - 实现多层次的缓存机制
6. **性能监控** - 建立完善的性能监控体系
7. **问题诊断与解决** - 识别和解决性能瓶颈
8. **最佳实践** - 总结性能优化的最佳实践

---

## 1. 查询执行原理

### 1.1 SQL 查询执行流程

```python
# query_execution_analysis.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import create_engine, text, event
from typing import Optional, List, Dict, Any
from datetime import datetime
import time
import logging

class QueryExecutionAnalyzer:
    """查询执行分析器"""
    
    def __init__(self, engine):
        self.engine = engine
        self.query_logs: List[Dict[str, Any]] = []
        self.setup_query_logging()
    
    def setup_query_logging(self):
        """设置查询日志记录"""
        @event.listens_for(self.engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            
        @event.listens_for(self.engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - context._query_start_time
            
            self.query_logs.append({
                'statement': statement,
                'parameters': parameters,
                'execution_time': total_time,
                'timestamp': datetime.utcnow(),
                'executemany': executemany
            })
    
    def analyze_query_plan(self, session: Session, query) -> Dict[str, Any]:
        """分析查询执行计划"""
        # 获取查询的 SQL 语句
        compiled_query = query.compile(compile_kwargs={"literal_binds": True})
        sql_statement = str(compiled_query)
        
        # 执行 EXPLAIN 分析
        explain_query = text(f"EXPLAIN QUERY PLAN {sql_statement}")
        
        try:
            result = session.execute(explain_query)
            plan_rows = result.fetchall()
            
            return {
                'sql': sql_statement,
                'execution_plan': [dict(row) for row in plan_rows],
                'analysis_time': datetime.utcnow()
            }
        except Exception as e:
            return {
                'sql': sql_statement,
                'error': str(e),
                'analysis_time': datetime.utcnow()
            }
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """获取查询统计信息"""
        if not self.query_logs:
            return {'message': '暂无查询数据'}
        
        execution_times = [log['execution_time'] for log in self.query_logs]
        
        return {
            'total_queries': len(self.query_logs),
            'average_execution_time': sum(execution_times) / len(execution_times),
            'min_execution_time': min(execution_times),
            'max_execution_time': max(execution_times),
            'total_execution_time': sum(execution_times),
            'slow_queries': [log for log in self.query_logs if log['execution_time'] > 1.0],
            'recent_queries': self.query_logs[-10:]  # 最近10个查询
        }
    
    def clear_logs(self):
        """清除查询日志"""
        self.query_logs.clear()

# 示例模型
class User(SQLModel, table=True):
    """用户模型"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True)
    email: str = Field(max_length=255, unique=True)
    age: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

class Post(SQLModel, table=True):
    """文章模型"""
    __tablename__ = "posts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    content: str
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    view_count: int = Field(default=0)
    is_published: bool = Field(default=False)

# 查询执行示例
def demonstrate_query_execution():
    """演示查询执行分析"""
    engine = create_engine("sqlite:///performance_demo.db", echo=False)
    
    # 创建分析器
    analyzer = QueryExecutionAnalyzer(engine)
    
    with Session(engine) as session:
        # 创建表
        SQLModel.metadata.create_all(engine)
        
        # 示例查询1：简单查询
        simple_query = select(User).where(User.is_active == True)
        users = session.exec(simple_query).all()
        
        # 示例查询2：连接查询
        join_query = select(User, Post).join(Post, User.id == Post.user_id)
        user_posts = session.exec(join_query).all()
        
        # 示例查询3：聚合查询
        from sqlalchemy import func
        aggregate_query = select(
            User.id,
            User.username,
            func.count(Post.id).label('post_count')
        ).join(Post, User.id == Post.user_id, isouter=True).group_by(User.id)
        
        user_stats = session.exec(aggregate_query).all()
        
        # 分析查询计划
        plan1 = analyzer.analyze_query_plan(session, simple_query)
        plan2 = analyzer.analyze_query_plan(session, join_query)
        plan3 = analyzer.analyze_query_plan(session, aggregate_query)
        
        print("简单查询执行计划:")
        print(plan1)
        print("\n连接查询执行计划:")
        print(plan2)
        print("\n聚合查询执行计划:")
        print(plan3)
        
        # 获取统计信息
        stats = analyzer.get_query_statistics()
        print("\n查询统计信息:")
        print(stats)
```

### 1.2 查询性能影响因素

```python
# performance_factors.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import Index, text, func
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import random
import time

class PerformanceFactorAnalyzer:
    """性能影响因素分析器"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def analyze_table_size_impact(self, model_class, sizes: List[int]) -> Dict[str, Any]:
        """分析表大小对查询性能的影响"""
        results = []
        
        for size in sizes:
            # 清空表
            self.session.execute(text(f"DELETE FROM {model_class.__tablename__}"))
            self.session.commit()
            
            # 插入测试数据
            self._insert_test_data(model_class, size)
            
            # 测试查询性能
            start_time = time.time()
            query = select(model_class).where(getattr(model_class, 'is_active') == True)
            result = self.session.exec(query).all()
            end_time = time.time()
            
            results.append({
                'table_size': size,
                'query_time': end_time - start_time,
                'result_count': len(result)
            })
        
        return {
            'analysis_type': 'table_size_impact',
            'results': results,
            'conclusion': self._analyze_size_impact_trend(results)
        }
    
    def analyze_index_impact(self, model_class, field_name: str) -> Dict[str, Any]:
        """分析索引对查询性能的影响"""
        table_name = model_class.__tablename__
        
        # 测试无索引的查询性能
        no_index_time = self._measure_query_time(
            select(model_class).where(getattr(model_class, field_name) == 'test_value')
        )
        
        # 创建索引
        index_name = f"idx_{table_name}_{field_name}"
        create_index_sql = text(f"CREATE INDEX {index_name} ON {table_name} ({field_name})")
        
        try:
            self.session.execute(create_index_sql)
            self.session.commit()
            
            # 测试有索引的查询性能
            with_index_time = self._measure_query_time(
                select(model_class).where(getattr(model_class, field_name) == 'test_value')
            )
            
            # 删除索引
            drop_index_sql = text(f"DROP INDEX {index_name}")
            self.session.execute(drop_index_sql)
            self.session.commit()
            
            return {
                'field': field_name,
                'no_index_time': no_index_time,
                'with_index_time': with_index_time,
                'performance_improvement': (no_index_time - with_index_time) / no_index_time * 100,
                'recommendation': 'beneficial' if with_index_time < no_index_time * 0.8 else 'marginal'
            }
            
        except Exception as e:
            return {
                'field': field_name,
                'error': str(e),
                'recommendation': 'analysis_failed'
            }
    
    def analyze_join_performance(self) -> Dict[str, Any]:
        """分析连接查询性能"""
        results = {}
        
        # 内连接
        inner_join_time = self._measure_query_time(
            select(User, Post).join(Post, User.id == Post.user_id)
        )
        
        # 左外连接
        left_join_time = self._measure_query_time(
            select(User, Post).join(Post, User.id == Post.user_id, isouter=True)
        )
        
        # 子查询方式
        subquery_time = self._measure_query_time(
            select(User).where(User.id.in_(
                select(Post.user_id).distinct()
            ))
        )
        
        return {
            'inner_join_time': inner_join_time,
            'left_join_time': left_join_time,
            'subquery_time': subquery_time,
            'fastest_method': min(
                ('inner_join', inner_join_time),
                ('left_join', left_join_time),
                ('subquery', subquery_time),
                key=lambda x: x[1]
            )[0]
        }
    
    def _insert_test_data(self, model_class, count: int):
        """插入测试数据"""
        if model_class == User:
            users = [
                User(
                    username=f"user_{i}",
                    email=f"user_{i}@example.com",
                    age=random.randint(18, 80),
                    is_active=random.choice([True, False])
                )
                for i in range(count)
            ]
            self.session.add_all(users)
        elif model_class == Post:
            posts = [
                Post(
                    title=f"Post {i}",
                    content=f"Content for post {i}",
                    user_id=random.randint(1, min(count, 100)),
                    view_count=random.randint(0, 1000),
                    is_published=random.choice([True, False])
                )
                for i in range(count)
            ]
            self.session.add_all(posts)
        
        self.session.commit()
    
    def _measure_query_time(self, query) -> float:
        """测量查询执行时间"""
        start_time = time.time()
        result = self.session.exec(query).all()
        end_time = time.time()
        return end_time - start_time
    
    def _analyze_size_impact_trend(self, results: List[Dict]) -> str:
        """分析表大小影响趋势"""
        if len(results) < 2:
            return "数据不足以分析趋势"
        
        # 计算性能下降率
        first_time = results[0]['query_time']
        last_time = results[-1]['query_time']
        
        if last_time > first_time * 2:
            return "表大小显著影响查询性能，建议优化"
        elif last_time > first_time * 1.5:
            return "表大小对查询性能有一定影响"
        else:
            return "表大小对查询性能影响较小"

# 使用示例
def analyze_performance_factors():
    """分析性能影响因素"""
    engine = create_engine("sqlite:///performance_analysis.db")
    
    with Session(engine) as session:
        SQLModel.metadata.create_all(engine)
        
        analyzer = PerformanceFactorAnalyzer(session)
        
        # 分析表大小影响
        size_impact = analyzer.analyze_table_size_impact(User, [100, 500, 1000, 5000])
        print("表大小影响分析:")
        print(size_impact)
        
        # 分析索引影响
        index_impact = analyzer.analyze_index_impact(User, 'username')
        print("\n索引影响分析:")
        print(index_impact)
        
        # 分析连接性能
        join_performance = analyzer.analyze_join_performance()
        print("\n连接查询性能分析:")
        print(join_performance)
```

---

## 2. 基础查询优化

### 2.1 查询语句优化

```python
# basic_query_optimization.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import func, and_, or_, text
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

class BasicQueryOptimizer:
    """基础查询优化器"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def optimize_select_fields(self, model_class, needed_fields: List[str]):
        """优化字段选择 - 只查询需要的字段"""
        # ❌ 错误：查询所有字段
        # query = select(model_class)
        
        # ✅ 正确：只查询需要的字段
        selected_fields = [getattr(model_class, field) for field in needed_fields]
        query = select(*selected_fields)
        
        return query
    
    def optimize_where_conditions(self, model_class):
        """优化 WHERE 条件"""
        examples = {}
        
        # ❌ 错误：使用函数在字段上
        # examples['bad_function'] = select(model_class).where(
        #     func.lower(model_class.username) == 'john'
        # )
        
        # ✅ 正确：避免在字段上使用函数
        examples['good_direct'] = select(model_class).where(
            model_class.username == 'john'  # 假设数据已经是正确格式
        )
        
        # ❌ 错误：使用 OR 条件（可能导致索引失效）
        examples['bad_or'] = select(model_class).where(
            or_(model_class.age > 30, model_class.age < 20)
        )
        
        # ✅ 正确：重写为更高效的条件
        examples['good_not_between'] = select(model_class).where(
            ~model_class.age.between(20, 30)
        )
        
        # ✅ 正确：使用 IN 替代多个 OR
        examples['good_in'] = select(model_class).where(
            model_class.id.in_([1, 2, 3, 4, 5])
        )
        
        return examples
    
    def optimize_limit_offset(self, model_class, page: int, page_size: int):
        """优化分页查询"""
        # ❌ 错误：大偏移量分页
        if page > 100:  # 大页码时性能很差
            # 使用游标分页替代偏移分页
            return self._cursor_based_pagination(model_class, page, page_size)
        
        # ✅ 正确：小偏移量时使用标准分页
        offset = (page - 1) * page_size
        query = select(model_class).offset(offset).limit(page_size)
        
        return query
    
    def _cursor_based_pagination(self, model_class, page: int, page_size: int):
        """基于游标的分页"""
        # 假设有一个 last_id 参数
        last_id = (page - 1) * page_size  # 简化示例
        
        query = select(model_class).where(
            model_class.id > last_id
        ).limit(page_size)
        
        return query
    
    def optimize_joins(self):
        """优化连接查询"""
        examples = {}
        
        # ✅ 正确：使用适当的连接类型
        examples['inner_join'] = select(User, Post).join(
            Post, User.id == Post.user_id
        )
        
        # ✅ 正确：在连接条件中使用索引字段
        examples['indexed_join'] = select(User, Post).join(
            Post, User.id == Post.user_id  # id 通常有索引
        )
        
        # ✅ 正确：预加载相关数据
        from sqlalchemy.orm import selectinload
        examples['eager_loading'] = select(User).options(
            selectinload(User.posts)  # 假设有关系定义
        )
        
        return examples
    
    def optimize_aggregations(self):
        """优化聚合查询"""
        examples = {}
        
        # ✅ 正确：使用索引字段进行分组
        examples['group_by_indexed'] = select(
            User.is_active,
            func.count(User.id).label('user_count')
        ).group_by(User.is_active)
        
        # ✅ 正确：使用 HAVING 过滤聚合结果
        examples['having_filter'] = select(
            Post.user_id,
            func.count(Post.id).label('post_count')
        ).group_by(Post.user_id).having(
            func.count(Post.id) > 5
        )
        
        # ✅ 正确：使用窗口函数替代子查询
        examples['window_function'] = select(
            User.id,
            User.username,
            func.row_number().over(
                partition_by=User.is_active,
                order_by=User.created_at.desc()
            ).label('rank')
        )
        
        return examples

class QueryOptimizationService:
    """查询优化服务"""
    
    def __init__(self, session: Session):
        self.session = session
        self.optimizer = BasicQueryOptimizer(session)
    
    def get_active_users_optimized(self, limit: int = 100) -> List[User]:
        """获取活跃用户 - 优化版本"""
        # 只查询需要的字段，使用索引字段过滤
        query = select(User.id, User.username, User.email).where(
            User.is_active == True
        ).limit(limit)
        
        return self.session.exec(query).all()
    
    def get_user_post_stats_optimized(self, user_id: int) -> Dict[str, Any]:
        """获取用户文章统计 - 优化版本"""
        # 使用单个查询获取所有统计信息
        stats_query = select(
            func.count(Post.id).label('total_posts'),
            func.count(Post.id).filter(Post.is_published == True).label('published_posts'),
            func.sum(Post.view_count).label('total_views'),
            func.avg(Post.view_count).label('avg_views')
        ).where(Post.user_id == user_id)
        
        result = self.session.exec(stats_query).first()
        
        return {
            'total_posts': result.total_posts or 0,
            'published_posts': result.published_posts or 0,
            'total_views': result.total_views or 0,
            'avg_views': float(result.avg_views or 0)
        }
    
    def get_popular_posts_optimized(self, days: int = 7, limit: int = 10) -> List[Post]:
        """获取热门文章 - 优化版本"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 使用复合条件和适当的排序
        query = select(Post).where(
            and_(
                Post.is_published == True,
                Post.created_at >= cutoff_date
            )
        ).order_by(
            Post.view_count.desc()
        ).limit(limit)
        
        return self.session.exec(query).all()
    
    def search_users_optimized(self, search_term: str, limit: int = 20) -> List[User]:
        """搜索用户 - 优化版本"""
        # 避免使用 LIKE '%term%'，使用前缀匹配
        search_pattern = f"{search_term}%"
        
        query = select(User).where(
            or_(
                User.username.like(search_pattern),
                User.email.like(search_pattern)
            )
        ).limit(limit)
        
        return self.session.exec(query).all()
```

### 2.2 查询重写技巧

```python
# query_rewriting.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import func, exists, and_, or_, case, text
from typing import Optional, List, Dict, Any, Tuple

class QueryRewriter:
    """查询重写器"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def rewrite_exists_queries(self):
        """重写 EXISTS 查询"""
        examples = {}
        
        # ❌ 低效：使用子查询检查存在性
        examples['inefficient_subquery'] = select(User).where(
            User.id.in_(
                select(Post.user_id).where(Post.is_published == True)
            )
        )
        
        # ✅ 高效：使用 EXISTS
        examples['efficient_exists'] = select(User).where(
            exists().where(
                and_(
                    Post.user_id == User.id,
                    Post.is_published == True
                )
            )
        )
        
        # ✅ 更高效：使用 JOIN（如果需要文章数据）
        examples['efficient_join'] = select(User).join(
            Post, and_(
                User.id == Post.user_id,
                Post.is_published == True
            )
        ).distinct()
        
        return examples
    
    def rewrite_count_queries(self):
        """重写计数查询"""
        examples = {}
        
        # ❌ 低效：使用 COUNT(*) 检查存在性
        examples['inefficient_count'] = select(
            func.count(Post.id)
        ).where(Post.user_id == 1)
        
        # ✅ 高效：使用 EXISTS 检查存在性
        examples['efficient_exists_check'] = select(
            exists().where(Post.user_id == 1)
        )
        
        # ✅ 高效：使用 LIMIT 1 获取示例
        examples['efficient_sample'] = select(Post).where(
            Post.user_id == 1
        ).limit(1)
        
        return examples
    
    def rewrite_union_queries(self):
        """重写 UNION 查询"""
        examples = {}
        
        # ❌ 低效：使用 UNION 合并相似查询
        active_users = select(User.id, User.username).where(User.is_active == True)
        inactive_users = select(User.id, User.username).where(User.is_active == False)
        examples['inefficient_union'] = active_users.union(inactive_users)
        
        # ✅ 高效：使用单个查询
        examples['efficient_single'] = select(
            User.id,
            User.username,
            User.is_active
        )
        
        return examples
    
    def rewrite_case_queries(self):
        """重写 CASE 查询"""
        examples = {}
        
        # ✅ 使用 CASE 表达式进行条件聚合
        examples['conditional_aggregation'] = select(
            User.is_active,
            func.count(User.id).label('total_users'),
            func.count(
                case(
                    (User.age >= 18, User.id),
                    else_=None
                )
            ).label('adult_users'),
            func.count(
                case(
                    (User.age < 18, User.id),
                    else_=None
                )
            ).label('minor_users')
        ).group_by(User.is_active)
        
        return examples
    
    def rewrite_window_function_queries(self):
        """重写窗口函数查询"""
        examples = {}
        
        # ❌ 低效：使用子查询计算排名
        examples['inefficient_ranking'] = select(
            User.id,
            User.username,
            select(func.count(User.id)).where(
                User.created_at <= User.created_at
            ).scalar_subquery().label('rank')
        )
        
        # ✅ 高效：使用窗口函数
        examples['efficient_window'] = select(
            User.id,
            User.username,
            func.row_number().over(
                order_by=User.created_at
            ).label('rank')
        )
        
        # ✅ 高效：使用窗口函数计算移动平均
        examples['moving_average'] = select(
            Post.id,
            Post.title,
            Post.view_count,
            func.avg(Post.view_count).over(
                order_by=Post.created_at,
                rows=(2, 0)  # 当前行和前两行
            ).label('moving_avg_views')
        )
        
        return examples
    
    def optimize_pagination_queries(self, last_id: Optional[int] = None, limit: int = 20):
        """优化分页查询"""
        if last_id is None:
            # 第一页
            query = select(User).order_by(User.id).limit(limit)
        else:
            # 后续页面使用游标分页
            query = select(User).where(
                User.id > last_id
            ).order_by(User.id).limit(limit)
        
        return query
    
    def optimize_search_queries(self, search_term: str):
        """优化搜索查询"""
        examples = {}
        
        # ❌ 低效：使用 LIKE '%term%'
        examples['inefficient_like'] = select(User).where(
            User.username.like(f"%{search_term}%")
        )
        
        # ✅ 较好：使用前缀匹配
        examples['prefix_match'] = select(User).where(
            User.username.like(f"{search_term}%")
        )
        
        # ✅ 最好：使用全文搜索（如果支持）
        examples['fulltext_search'] = select(User).where(
            text("MATCH(username) AGAINST(:search_term IN BOOLEAN MODE)")
        ).params(search_term=search_term)
        
        return examples

class AdvancedQueryOptimizer:
    """高级查询优化器"""
    
    def __init__(self, session: Session):
        self.session = session
        self.rewriter = QueryRewriter(session)
    
    def get_user_activity_summary(self, user_id: int) -> Dict[str, Any]:
        """获取用户活动摘要 - 优化版本"""
        # 使用单个查询获取所有相关统计
        query = select(
            func.count(Post.id).label('total_posts'),
            func.count(Post.id).filter(Post.is_published == True).label('published_posts'),
            func.sum(Post.view_count).label('total_views'),
            func.max(Post.created_at).label('last_post_date'),
            func.avg(
                case(
                    (Post.is_published == True, Post.view_count),
                    else_=None
                )
            ).label('avg_published_views')
        ).where(Post.user_id == user_id)
        
        result = self.session.exec(query).first()
        
        return {
            'total_posts': result.total_posts or 0,
            'published_posts': result.published_posts or 0,
            'total_views': result.total_views or 0,
            'last_post_date': result.last_post_date,
            'avg_published_views': float(result.avg_published_views or 0)
        }
    
    def get_trending_content(self, days: int = 7) -> List[Dict[str, Any]]:
        """获取趋势内容 - 使用窗口函数"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(
            Post.id,
            Post.title,
            Post.view_count,
            User.username,
            func.rank().over(
                order_by=Post.view_count.desc()
            ).label('view_rank'),
            func.percent_rank().over(
                order_by=Post.view_count
            ).label('view_percentile')
        ).join(
            User, Post.user_id == User.id
        ).where(
            and_(
                Post.created_at >= cutoff_date,
                Post.is_published == True
            )
        ).order_by(
            Post.view_count.desc()
        ).limit(50)
        
        results = self.session.exec(query).all()
        
        return [
            {
                'id': row.id,
                'title': row.title,
                'view_count': row.view_count,
                'author': row.username,
                'rank': row.view_rank,
                'percentile': float(row.view_percentile)
            }
            for row in results
        ]
    
    def get_user_engagement_metrics(self) -> List[Dict[str, Any]]:
        """获取用户参与度指标 - 复杂聚合查询优化"""
        query = select(
            User.id,
            User.username,
            func.count(Post.id).label('post_count'),
            func.sum(Post.view_count).label('total_views'),
            func.avg(Post.view_count).label('avg_views_per_post'),
            func.count(Post.id).filter(Post.is_published == True).label('published_count'),
            func.max(Post.created_at).label('last_activity'),
            # 计算参与度分数
            (
                func.count(Post.id) * 0.3 +
                func.sum(Post.view_count) * 0.0001 +
                func.count(Post.id).filter(Post.is_published == True) * 0.5
            ).label('engagement_score')
        ).join(
            Post, User.id == Post.user_id, isouter=True
        ).group_by(
            User.id, User.username
        ).having(
            func.count(Post.id) > 0  # 只包含有文章的用户
        ).order_by(
            text('engagement_score DESC')
        )
        
        results = self.session.exec(query).all()
        
        return [
            {
                'user_id': row.id,
                'username': row.username,
                'post_count': row.post_count,
                'total_views': row.total_views or 0,
                'avg_views_per_post': float(row.avg_views_per_post or 0),
                'published_count': row.published_count,
                'last_activity': row.last_activity,
                'engagement_score': float(row.engagement_score or 0)
            }
            for row in results
        ]
```

---

## 3. 索引策略

### 3.1 索引设计原则

```python
# index_strategy.py
from sqlmodel import SQLModel, Field
from sqlalchemy import Index, text, UniqueConstraint
from typing import Optional, List, Dict, Any
from datetime import datetime

class OptimizedUserModel(SQLModel, table=True):
    """优化索引的用户模型"""
    __tablename__ = "optimized_users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True)  # 自动创建唯一索引
    email: str = Field(max_length=255, unique=True)    # 自动创建唯一索引
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    age: Optional[int] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)
    
    __table_args__ = (
        # 1. 单列索引 - 用于频繁的单字段查询
        Index('idx_users_age', 'age'),  # 年龄查询
        Index('idx_users_is_active', 'is_active'),  # 状态查询
        Index('idx_users_created_at', 'created_at'),  # 时间排序
        
        # 2. 复合索引 - 用于多字段查询
        Index('idx_users_active_created', 'is_active', 'created_at'),  # 活跃用户按时间排序
        Index('idx_users_name_search', 'last_name', 'first_name'),  # 姓名搜索
        
        # 3. 部分索引 - 只为特定条件的行创建索引
        Index('idx_users_active_last_login', 'last_login', 
              postgresql_where=text("is_active = true")),
        
        # 4. 函数索引 - 用于函数查询
        Index('idx_users_email_lower', text('lower(email)')),  # 大小写不敏感搜索
        Index('idx_users_full_name', text('first_name || " " || last_name')),  # 全名搜索
        
        # 5. 覆盖索引 - 包含查询所需的所有列
        Index('idx_users_profile_lookup', 'username', 'first_name', 'last_name', 'email'),
    )

class OptimizedPostModel(SQLModel, table=True):
    """优化索引的文章模型"""
    __tablename__ = "optimized_posts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    content: str
    user_id: int = Field(foreign_key="optimized_users.id")
    category_id: Optional[int] = Field(default=None)
    is_published: bool = Field(default=False)
    view_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    __table_args__ = (
        # 外键索引
        Index('idx_posts_user_id', 'user_id'),
        Index('idx_posts_category_id', 'category_id'),
        
        # 状态和时间索引
        Index('idx_posts_published_created', 'is_published', 'created_at'),
        Index('idx_posts_published_views', 'is_published', 'view_count'),
        
        # 用户文章索引
        Index('idx_posts_user_published', 'user_id', 'is_published', 'created_at'),
        
        # 热门文章索引
        Index('idx_posts_hot', 'view_count', 'created_at', 
              postgresql_where=text("is_published = true")),
        
        # 全文搜索索引（PostgreSQL）
        Index('idx_posts_fulltext', text('to_tsvector(\'english\', title || \' \' || content)'),
              postgresql_using='gin'),
    )

class IndexAnalyzer:
    """索引分析器"""
    
    def __init__(self, session):
        self.session = session
    
    def analyze_index_usage(self, table_name: str) -> Dict[str, Any]:
        """分析索引使用情况（PostgreSQL）"""
        query = text("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_tup_read,
                idx_tup_fetch,
                idx_scan,
                CASE 
                    WHEN idx_scan = 0 THEN 'Unused'
                    WHEN idx_scan < 10 THEN 'Low Usage'
                    WHEN idx_scan < 100 THEN 'Medium Usage'
                    ELSE 'High Usage'
                END as usage_level
            FROM pg_stat_user_indexes 
            WHERE tablename = :table_name
            ORDER BY idx_scan DESC
        """)
        
        try:
            result = self.session.execute(query, {'table_name': table_name})
            return {
                'table': table_name,
                'indexes': [dict(row) for row in result.fetchall()]
            }
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_index_size(self, table_name: str) -> Dict[str, Any]:
        """分析索引大小（PostgreSQL）"""
        query = text("""
            SELECT 
                indexname,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as size,
                pg_relation_size(indexname::regclass) as size_bytes
            FROM pg_indexes 
            WHERE tablename = :table_name
            ORDER BY pg_relation_size(indexname::regclass) DESC
        """)
        
        try:
            result = self.session.execute(query, {'table_name': table_name})
            return {
                'table': table_name,
                'index_sizes': [dict(row) for row in result.fetchall()]
            }
        except Exception as e:
            return {'error': str(e)}
    
    def suggest_missing_indexes(self, table_name: str) -> List[str]:
        """建议缺失的索引"""
        # 分析慢查询日志，找出可能需要索引的查询
        suggestions = []
        
        # 这里是一个简化的示例，实际应该分析查询日志
        common_patterns = [
            f"CREATE INDEX idx_{table_name}_status_date ON {table_name} (status, created_at);",
            f"CREATE INDEX idx_{table_name}_user_status ON {table_name} (user_id, status);",
            f"CREATE INDEX idx_{table_name}_search ON {table_name} USING gin(to_tsvector('english', title));"
        ]
        
        return common_patterns
    
    def check_duplicate_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """检查重复索引"""
        query = text("""
            SELECT 
                i1.indexname as index1,
                i2.indexname as index2,
                i1.indexdef as definition1,
                i2.indexdef as definition2
            FROM pg_indexes i1
            JOIN pg_indexes i2 ON i1.tablename = i2.tablename
            WHERE i1.tablename = :table_name
            AND i1.indexname < i2.indexname
            AND i1.indexdef = i2.indexdef
        """)
        
        try:
            result = self.session.execute(query, {'table_name': table_name})
            return [dict(row) for row in result.fetchall()]
        except Exception as e:
            return [{'error': str(e)}]

class IndexOptimizationService:
    """索引优化服务"""
    
    def __init__(self, session):
        self.session = session
        self.analyzer = IndexAnalyzer(session)
    
    def create_optimal_indexes(self, model_class):
        """为模型创建最优索引"""
        table_name = model_class.__tablename__
        
        # 基于查询模式创建索引
        index_commands = []
        
        if hasattr(model_class, 'user_id'):
            # 外键索引
            index_commands.append(
                f"CREATE INDEX IF NOT EXISTS idx_{table_name}_user_id ON {table_name} (user_id);"
            )
        
        if hasattr(model_class, 'created_at'):
            # 时间索引
            index_commands.append(
                f"CREATE INDEX IF NOT EXISTS idx_{table_name}_created_at ON {table_name} (created_at);"
            )
        
        if hasattr(model_class, 'is_active') or hasattr(model_class, 'is_published'):
            # 状态索引
            status_field = 'is_active' if hasattr(model_class, 'is_active') else 'is_published'
            index_commands.append(
                f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{status_field} ON {table_name} ({status_field});"
            )
        
        # 执行索引创建
        for command in index_commands:
            try:
                self.session.execute(text(command))
                self.session.commit()
            except Exception as e:
                print(f"Failed to create index: {command}, Error: {e}")
                self.session.rollback()
        
        return index_commands
    
    def optimize_existing_indexes(self, table_name: str) -> Dict[str, Any]:
        """优化现有索引"""
        # 分析索引使用情况
        usage_analysis = self.analyzer.analyze_index_usage(table_name)
        size_analysis = self.analyzer.analyze_index_size(table_name)
        duplicate_indexes = self.analyzer.check_duplicate_indexes(table_name)
        
        optimization_plan = {
            'unused_indexes': [],
            'duplicate_indexes': duplicate_indexes,
            'large_indexes': [],
            'recommendations': []
        }
        
        # 找出未使用的索引
        if 'indexes' in usage_analysis:
            for index in usage_analysis['indexes']:
                if index['usage_level'] == 'Unused':
                    optimization_plan['unused_indexes'].append(index['indexname'])
        
        # 找出过大的索引
        if 'index_sizes' in size_analysis:
            for index in size_analysis['index_sizes']:
                if index['size_bytes'] > 100 * 1024 * 1024:  # 100MB
                    optimization_plan['large_indexes'].append(index)
        
        # 生成优化建议
        if optimization_plan['unused_indexes']:
            optimization_plan['recommendations'].append(
                f"Consider dropping unused indexes: {', '.join(optimization_plan['unused_indexes'])}"
            )
        
        if optimization_plan['duplicate_indexes']:
            optimization_plan['recommendations'].append(
                "Remove duplicate indexes to save space and improve write performance"
            )
        
        return optimization_plan
```

### 3.2 索引监控与维护

```python
# index_monitoring.py
from sqlmodel import Session
from sqlalchemy import text, event
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import time
import logging

class IndexMonitor:
    """索引监控器"""
    
    def __init__(self, session: Session):
        self.session = session
        self.logger = logging.getLogger(__name__)
        self.query_stats: List[Dict[str, Any]] = []
        self.setup_monitoring()
    
    def setup_monitoring(self):
        """设置监控事件"""
        @event.listens_for(self.session.bind, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            context._statement = statement
            
        @event.listens_for(self.session.bind, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - context._query_start_time
            
            # 记录慢查询
            if total_time > 1.0:  # 超过1秒的查询
                self.query_stats.append({
                    'statement': statement,
                    'execution_time': total_time,
                    'timestamp': datetime.utcnow(),
                    'parameters': parameters
                })
                
                self.logger.warning(f"Slow query detected: {total_time:.2f}s - {statement[:100]}...")
    
    def get_index_hit_ratio(self) -> Dict[str, float]:
        """获取索引命中率（PostgreSQL）"""
        query = text("""
            SELECT 
                schemaname,
                tablename,
                CASE 
                    WHEN seq_tup_read + idx_tup_fetch = 0 THEN 0
                    ELSE idx_tup_fetch::float / (seq_tup_read + idx_tup_fetch) * 100
                END as index_hit_ratio
            FROM pg_stat_user_tables
            ORDER BY index_hit_ratio DESC
        """)
        
        try:
            result = self.session.execute(query)
            return {f"{row.schemaname}.{row.tablename}": row.index_hit_ratio for row in result.fetchall()}
        except Exception as e:
            self.logger.error(f"Failed to get index hit ratio: {e}")
            return {}
    
    def get_table_scan_ratio(self) -> Dict[str, float]:
        """获取表扫描比率"""
        query = text("""
            SELECT 
                schemaname,
                tablename,
                seq_scan,
                idx_scan,
                CASE 
                    WHEN seq_scan + idx_scan = 0 THEN 0
                    ELSE seq_scan::float / (seq_scan + idx_scan) * 100
                END as table_scan_ratio
            FROM pg_stat_user_tables
            WHERE seq_scan + idx_scan > 0
            ORDER BY table_scan_ratio DESC
        """)
        
        try:
            result = self.session.execute(query)
            return {
                f"{row.schemaname}.{row.tablename}": {
                    'table_scan_ratio': row.table_scan_ratio,
                    'seq_scan': row.seq_scan,
                    'idx_scan': row.idx_scan
                }
                for row in result.fetchall()
            }
        except Exception as e:
            self.logger.error(f"Failed to get table scan ratio: {e}")
            return {}
    
    def analyze_slow_queries(self, threshold: float = 1.0) -> List[Dict[str, Any]]:
        """分析慢查询"""
        slow_queries = [q for q in self.query_stats if q['execution_time'] > threshold]
        
        # 按执行时间排序
        slow_queries.sort(key=lambda x: x['execution_time'], reverse=True)
        
        # 分析查询模式
        analysis = []
        for query in slow_queries[:10]:  # 取前10个最慢的查询
            analysis.append({
                'statement': query['statement'][:200] + '...' if len(query['statement']) > 200 else query['statement'],
                'execution_time': query['execution_time'],
                'timestamp': query['timestamp'],
                'potential_issues': self._analyze_query_issues(query['statement'])
            })
        
        return analysis
    
    def _analyze_query_issues(self, statement: str) -> List[str]:
        """分析查询潜在问题"""
        issues = []
        statement_lower = statement.lower()
        
        if 'select *' in statement_lower:
            issues.append("Using SELECT * - consider selecting only needed columns")
        
        if 'like \'%' in statement_lower:
            issues.append("Using LIKE with leading wildcard - consider full-text search")
        
        if 'order by' in statement_lower and 'limit' not in statement_lower:
            issues.append("ORDER BY without LIMIT - might be sorting large result set")
        
        if statement_lower.count('join') > 3:
            issues.append("Multiple JOINs - consider query optimization")
        
        if 'or' in statement_lower:
            issues.append("OR conditions - might prevent index usage")
        
        return issues
    
    def get_index_maintenance_recommendations(self) -> List[Dict[str, Any]]:
        """获取索引维护建议"""
        recommendations = []
        
        # 检查索引膨胀
        bloat_query = text("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                pg_size_pretty(pg_relation_size(indexrelid)) as size,
                CASE 
                    WHEN pg_relation_size(indexrelid) > 100 * 1024 * 1024 THEN 'Consider REINDEX'
                    ELSE 'OK'
                END as recommendation
            FROM pg_stat_user_indexes
            WHERE pg_relation_size(indexrelid) > 50 * 1024 * 1024  -- 50MB以上的索引
            ORDER BY pg_relation_size(indexrelid) DESC
        """)
        
        try:
            result = self.session.execute(bloat_query)
            for row in result.fetchall():
                if row.recommendation != 'OK':
                    recommendations.append({
                        'type': 'index_maintenance',
                        'table': f"{row.schemaname}.{row.tablename}",
                        'index': row.indexname,
                        'size': row.size,
                        'action': row.recommendation,
                        'priority': 'high' if 'REINDEX' in row.recommendation else 'medium'
                    })
        except Exception as e:
            self.logger.error(f"Failed to check index bloat: {e}")
        
        # 检查未使用的索引
        unused_query = text("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan
            FROM pg_stat_user_indexes
            WHERE idx_scan = 0
            AND indexname NOT LIKE '%_pkey'  -- 排除主键
        """)
        
        try:
            result = self.session.execute(unused_query)
            for row in result.fetchall():
                recommendations.append({
                    'type': 'unused_index',
                    'table': f"{row.schemaname}.{row.tablename}",
                    'index': row.indexname,
                    'scan_count': row.idx_scan,
                    'action': 'Consider dropping unused index',
                    'priority': 'low'
                })
        except Exception as e:
            self.logger.error(f"Failed to check unused indexes: {e}")
        
        return recommendations
    
    def generate_maintenance_script(self, recommendations: List[Dict[str, Any]]) -> str:
        """生成维护脚本"""
        script_lines = [
            "-- Index Maintenance Script",
            f"-- Generated on {datetime.utcnow()}",
            ""
        ]
        
        # 重建索引
        reindex_commands = []
        for rec in recommendations:
            if rec['type'] == 'index_maintenance' and 'REINDEX' in rec['action']:
                reindex_commands.append(f"REINDEX INDEX {rec['index']};")
        
        if reindex_commands:
            script_lines.extend([
                "-- Rebuild large indexes",
                "-- Run during maintenance window"
            ])
            script_lines.extend(reindex_commands)
            script_lines.append("")
        
        # 删除未使用的索引
        drop_commands = []
        for rec in recommendations:
            if rec['type'] == 'unused_index':
                drop_commands.append(f"-- DROP INDEX {rec['index']};  -- Unused index on {rec['table']}")
        
        if drop_commands:
            script_lines.extend([
                "-- Drop unused indexes (review carefully before executing)",
                "-- Uncomment after verification"
            ])
            script_lines.extend(drop_commands)
            script_lines.append("")
        
        # 统计信息更新
        script_lines.extend([
            "-- Update table statistics",
            "ANALYZE;",
            "",
            "-- Check index usage after maintenance",
            "-- SELECT * FROM pg_stat_user_indexes WHERE schemaname = 'public';"
        ])
        
        return "\n".join(script_lines)

class IndexPerformanceTracker:
    """索引性能跟踪器"""
    
    def __init__(self, session: Session):
        self.session = session
        self.baseline_stats: Dict[str, Any] = {}
    
    def capture_baseline(self):
        """捕获基线性能数据"""
        self.baseline_stats = {
            'timestamp': datetime.utcnow(),
            'index_usage': self._get_index_usage_stats(),
            'table_stats': self._get_table_stats(),
            'query_performance': self._get_query_performance_stats()
        }
    
    def compare_performance(self) -> Dict[str, Any]:
        """比较当前性能与基线"""
        if not self.baseline_stats:
            return {'error': 'No baseline captured'}
        
        current_stats = {
            'timestamp': datetime.utcnow(),
            'index_usage': self._get_index_usage_stats(),
            'table_stats': self._get_table_stats(),
            'query_performance': self._get_query_performance_stats()
        }
        
        comparison = {
            'baseline_time': self.baseline_stats['timestamp'],
            'current_time': current_stats['timestamp'],
            'improvements': [],
            'regressions': [],
            'summary': {}
        }
        
        # 比较索引使用情况
        baseline_idx = self.baseline_stats['index_usage']
        current_idx = current_stats['index_usage']
        
        for table, current_ratio in current_idx.items():
            if table in baseline_idx:
                baseline_ratio = baseline_idx[table]
                diff = current_ratio - baseline_ratio
                
                if diff > 5:  # 提升超过5%
                    comparison['improvements'].append({
                        'type': 'index_hit_ratio',
                        'table': table,
                        'improvement': f"{diff:.1f}%",
                        'baseline': f"{baseline_ratio:.1f}%",
                        'current': f"{current_ratio:.1f}%"
                    })
                elif diff < -5:  # 下降超过5%
                    comparison['regressions'].append({
                        'type': 'index_hit_ratio',
                        'table': table,
                        'regression': f"{abs(diff):.1f}%",
                        'baseline': f"{baseline_ratio:.1f}%",
                        'current': f"{current_ratio:.1f}%"
                    })
        
        # 生成摘要
        comparison['summary'] = {
            'total_improvements': len(comparison['improvements']),
            'total_regressions': len(comparison['regressions']),
            'overall_trend': 'improving' if len(comparison['improvements']) > len(comparison['regressions']) else 'declining' if len(comparison['regressions']) > 0 else 'stable'
        }
        
        return comparison
    
    def _get_index_usage_stats(self) -> Dict[str, float]:
        """获取索引使用统计"""
        query = text("""
            SELECT 
                tablename,
                CASE 
                    WHEN seq_tup_read + idx_tup_fetch = 0 THEN 0
                    ELSE idx_tup_fetch::float / (seq_tup_read + idx_tup_fetch) * 100
                END as index_hit_ratio
            FROM pg_stat_user_tables
        """)
        
        try:
            result = self.session.execute(query)
            return {row.tablename: row.index_hit_ratio for row in result.fetchall()}
        except Exception:
            return {}
    
    def _get_table_stats(self) -> Dict[str, Any]:
        """获取表统计信息"""
        query = text("""
            SELECT 
                tablename,
                n_tup_ins,
                n_tup_upd,
                n_tup_del,
                seq_scan,
                idx_scan
            FROM pg_stat_user_tables
        """)
        
        try:
            result = self.session.execute(query)
            return {
                row.tablename: {
                    'inserts': row.n_tup_ins,
                    'updates': row.n_tup_upd,
                    'deletes': row.n_tup_del,
                    'seq_scans': row.seq_scan,
                    'index_scans': row.idx_scan
                }
                for row in result.fetchall()
            }
        except Exception:
            return {}
    
    def _get_query_performance_stats(self) -> Dict[str, Any]:
        """获取查询性能统计"""
        # 这里可以集成 pg_stat_statements 扩展的数据
        # 简化示例
        return {
            'avg_query_time': 0.1,  # 平均查询时间
            'slow_query_count': 0,  # 慢查询数量
            'total_queries': 1000   # 总查询数
        }

# 使用示例
def demonstrate_index_monitoring():
    """演示索引监控"""
    engine = create_engine("postgresql://user:pass@localhost/db")
    
    with Session(engine) as session:
        # 创建监控器
        monitor = IndexMonitor(session)
        tracker = IndexPerformanceTracker(session)
        
        # 捕获基线
        tracker.capture_baseline()
        
        # 模拟一些查询操作
        # ... 执行业务查询 ...
        
        # 分析性能
        hit_ratios = monitor.get_index_hit_ratio()
        scan_ratios = monitor.get_table_scan_ratio()
        slow_queries = monitor.analyze_slow_queries()
        
        print("索引命中率:")
        for table, ratio in hit_ratios.items():
            print(f"  {table}: {ratio:.1f}%")
        
        print("\n表扫描比率:")
        for table, stats in scan_ratios.items():
            print(f"  {table}: {stats['table_scan_ratio']:.1f}%")
        
        print("\n慢查询分析:")
        for query in slow_queries[:3]:  # 显示前3个
            print(f"  时间: {query['execution_time']:.2f}s")
            print(f"  语句: {query['statement'][:100]}...")
            print(f"  问题: {', '.join(query['potential_issues'])}")
            print()
        
        # 获取维护建议
        recommendations = monitor.get_index_maintenance_recommendations()
        if recommendations:
            print("维护建议:")
            for rec in recommendations:
                print(f"  {rec['type']}: {rec['action']} ({rec['priority']} priority)")
            
            # 生成维护脚本
            script = monitor.generate_maintenance_script(recommendations)
            print("\n维护脚本:")
            print(script)
        
        # 性能比较
        time.sleep(1)  # 模拟时间间隔
        comparison = tracker.compare_performance()
        print("\n性能比较:")
        print(f"总体趋势: {comparison['summary']['overall_trend']}")
        print(f"改进项: {comparison['summary']['total_improvements']}")
        print(f"退化项: {comparison['summary']['total_regressions']}")

---

## 4. 高级优化技术

### 4.1 查询计划优化

```python
# query_plan_optimization.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import text, func, and_, or_, case
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import json

class QueryPlanAnalyzer:
    """查询计划分析器"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def analyze_execution_plan(self, query, analyze: bool = True) -> Dict[str, Any]:
        """分析查询执行计划"""
        # 编译查询为SQL
        compiled_query = query.compile(
            compile_kwargs={"literal_binds": True}
        )
        sql_statement = str(compiled_query)
        
        # 获取执行计划
        explain_type = "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)" if analyze else "EXPLAIN (FORMAT JSON)"
        explain_query = text(f"{explain_type} {sql_statement}")
        
        try:
            result = self.session.execute(explain_query)
            plan_json = result.scalar()
            
            if isinstance(plan_json, str):
                plan_data = json.loads(plan_json)
            else:
                plan_data = plan_json
            
            return self._parse_execution_plan(plan_data[0]['Plan'])
            
        except Exception as e:
            return {
                'error': str(e),
                'sql': sql_statement
            }
    
    def _parse_execution_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """解析执行计划"""
        analysis = {
            'node_type': plan.get('Node Type'),
            'total_cost': plan.get('Total Cost'),
            'startup_cost': plan.get('Startup Cost'),
            'plan_rows': plan.get('Plan Rows'),
            'plan_width': plan.get('Plan Width'),
            'actual_time': plan.get('Actual Total Time'),
            'actual_rows': plan.get('Actual Rows'),
            'relation_name': plan.get('Relation Name'),
            'index_name': plan.get('Index Name'),
            'join_type': plan.get('Join Type'),
            'issues': [],
            'recommendations': [],
            'children': []
        }
        
        # 分析潜在问题
        self._analyze_plan_issues(plan, analysis)
        
        # 递归分析子节点
        if 'Plans' in plan:
            for child_plan in plan['Plans']:
                analysis['children'].append(self._parse_execution_plan(child_plan))
        
        return analysis
    
    def _analyze_plan_issues(self, plan: Dict[str, Any], analysis: Dict[str, Any]):
        """分析计划中的问题"""
        node_type = plan.get('Node Type', '')
        
        # 检查顺序扫描
        if node_type == 'Seq Scan':
            analysis['issues'].append('Sequential scan detected')
            analysis['recommendations'].append('Consider adding an index')
        
        # 检查嵌套循环连接
        if node_type == 'Nested Loop' and plan.get('Actual Rows', 0) > 1000:
            analysis['issues'].append('Nested loop with many rows')
            analysis['recommendations'].append('Consider hash join or merge join')
        
        # 检查排序操作
        if node_type == 'Sort' and plan.get('Sort Method') == 'external merge':
            analysis['issues'].append('External sort (disk-based)')
            analysis['recommendations'].append('Increase work_mem or add index for ordering')
        
        # 检查行数估计偏差
        plan_rows = plan.get('Plan Rows', 0)
        actual_rows = plan.get('Actual Rows', 0)
        if plan_rows > 0 and actual_rows > 0:
            ratio = max(plan_rows, actual_rows) / min(plan_rows, actual_rows)
            if ratio > 10:
                analysis['issues'].append(f'Row estimation off by {ratio:.1f}x')
                analysis['recommendations'].append('Update table statistics with ANALYZE')
    
    def suggest_query_optimizations(self, query) -> List[Dict[str, Any]]:
        """建议查询优化"""
        plan_analysis = self.analyze_execution_plan(query)
        suggestions = []
        
        # 基于执行计划生成建议
        def extract_suggestions(node: Dict[str, Any]):
            if node.get('issues'):
                suggestions.extend([
                    {
                        'issue': issue,
                        'recommendation': rec,
                        'node_type': node.get('node_type'),
                        'relation': node.get('relation_name')
                    }
                    for issue, rec in zip(node['issues'], node['recommendations'])
                ])
            
            for child in node.get('children', []):
                extract_suggestions(child)
        
        extract_suggestions(plan_analysis)
        return suggestions

class QueryOptimizationStrategies:
    """查询优化策略"""
    
    def __init__(self, session: Session):
        self.session = session
        self.analyzer = QueryPlanAnalyzer(session)
    
    def optimize_join_order(self, base_query):
        """优化连接顺序"""
        strategies = {}
        
        # 策略1：小表驱动大表
        strategies['small_to_large'] = select(User, Post).join(
            Post, User.id == Post.user_id
        ).where(
            User.is_active == True  # 先过滤用户
        )
        
        # 策略2：使用子查询预过滤
        active_user_ids = select(User.id).where(User.is_active == True)
        strategies['subquery_filter'] = select(User, Post).join(
            Post, User.id == Post.user_id
        ).where(
            User.id.in_(active_user_ids)
        )
        
        # 策略3：使用EXISTS替代JOIN
        strategies['exists_filter'] = select(User).where(
            exists().where(
                and_(
                    Post.user_id == User.id,
                    Post.is_published == True
                )
            )
        )
        
        return strategies
    
    def optimize_subqueries(self):
        """优化子查询"""
        optimizations = {}
        
        # 原始查询：相关子查询
        original_correlated = select(User).where(
            User.id.in_(
                select(Post.user_id).where(
                    and_(
                        Post.user_id == User.id,
                        Post.view_count > 1000
                    )
                )
            )
        )
        
        # 优化1：转换为JOIN
        optimizations['join_conversion'] = select(User).join(
            Post, User.id == Post.user_id
        ).where(
            Post.view_count > 1000
        ).distinct()
        
        # 优化2：使用EXISTS
        optimizations['exists_conversion'] = select(User).where(
            exists().where(
                and_(
                    Post.user_id == User.id,
                    Post.view_count > 1000
                )
            )
        )
        
        # 优化3：使用窗口函数替代子查询
        optimizations['window_function'] = select(
            User.id,
            User.username,
            func.max(Post.view_count).over(
                partition_by=User.id
            ).label('max_views')
        ).join(
            Post, User.id == Post.user_id
        ).where(
            Post.view_count > 1000
        )
        
        return optimizations
    
    def optimize_aggregations(self):
        """优化聚合查询"""
        optimizations = {}
        
        # 优化1：使用过滤聚合
        optimizations['filtered_aggregation'] = select(
            User.id,
            User.username,
            func.count(Post.id).label('total_posts'),
            func.count(Post.id).filter(Post.is_published == True).label('published_posts'),
            func.sum(
                case(
                    (Post.is_published == True, Post.view_count),
                    else_=0
                )
            ).label('published_views')
        ).join(
            Post, User.id == Post.user_id, isouter=True
        ).group_by(User.id, User.username)
        
        # 优化2：使用部分索引的聚合
        optimizations['indexed_aggregation'] = select(
            func.date_trunc('day', Post.created_at).label('date'),
            func.count(Post.id).label('post_count'),
            func.sum(Post.view_count).label('total_views')
        ).where(
            and_(
                Post.is_published == True,  # 使用索引字段
                Post.created_at >= datetime.utcnow() - timedelta(days=30)
            )
        ).group_by(
            func.date_trunc('day', Post.created_at)
        ).order_by(
            func.date_trunc('day', Post.created_at)
        )
        
        return optimizations
    
    def benchmark_query_strategies(self, strategies: Dict[str, Any]) -> Dict[str, Any]:
        """基准测试查询策略"""
        results = {}
        
        for name, query in strategies.items():
            # 测试执行时间
            start_time = time.time()
            try:
                result = self.session.exec(query).all()
                execution_time = time.time() - start_time
                
                # 分析执行计划
                plan_analysis = self.analyzer.analyze_execution_plan(query, analyze=False)
                
                results[name] = {
                    'execution_time': execution_time,
                    'result_count': len(result),
                    'total_cost': plan_analysis.get('total_cost'),
                    'issues': plan_analysis.get('issues', []),
                    'recommendations': plan_analysis.get('recommendations', [])
                }
                
            except Exception as e:
                results[name] = {
                    'error': str(e),
                    'execution_time': None
                }
        
        # 找出最佳策略
        valid_results = {k: v for k, v in results.items() if 'error' not in v}
        if valid_results:
            best_strategy = min(valid_results.items(), key=lambda x: x[1]['execution_time'])
            results['best_strategy'] = {
                'name': best_strategy[0],
                'execution_time': best_strategy[1]['execution_time'],
                'improvement_over_others': {
                    other_name: (
                        (other_data['execution_time'] - best_strategy[1]['execution_time']) / 
                        best_strategy[1]['execution_time'] * 100
                    )
                    for other_name, other_data in valid_results.items()
                    if other_name != best_strategy[0] and other_data['execution_time']
                }
            }
        
        return results

# 使用示例
def demonstrate_query_optimization():
    """演示查询优化"""
    engine = create_engine("postgresql://user:pass@localhost/db")
    
    with Session(engine) as session:
        optimizer = QueryOptimizationStrategies(session)
        
        # 测试连接优化策略
        join_strategies = optimizer.optimize_join_order(None)
        join_results = optimizer.benchmark_query_strategies(join_strategies)
        
        print("连接优化结果:")
        for strategy, result in join_results.items():
            if strategy != 'best_strategy' and 'error' not in result:
                print(f"  {strategy}: {result['execution_time']:.3f}s")
        
        if 'best_strategy' in join_results:
            best = join_results['best_strategy']
            print(f"\n最佳策略: {best['name']} ({best['execution_time']:.3f}s)")
        
        # 测试子查询优化
        subquery_strategies = optimizer.optimize_subqueries()
        subquery_results = optimizer.benchmark_query_strategies(subquery_strategies)
        
        print("\n子查询优化结果:")
        for strategy, result in subquery_results.items():
            if strategy != 'best_strategy' and 'error' not in result:
                print(f"  {strategy}: {result['execution_time']:.3f}s")
```

### 4.2 并行查询优化

```python
# parallel_query_optimization.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import text, func, create_engine
from sqlalchemy.pool import QueuePool
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable
import asyncio
import asyncpg
import time

class ParallelQueryExecutor:
    """并行查询执行器"""
    
    def __init__(self, engine, max_workers: int = 4):
        self.engine = engine
        self.max_workers = max_workers
    
    def execute_parallel_queries(self, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """并行执行多个查询"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有查询任务
            future_to_query = {
                executor.submit(self._execute_single_query, query_info): query_info['name']
                for query_info in queries
            }
            
            # 收集结果
            for future in as_completed(future_to_query):
                query_name = future_to_query[future]
                try:
                    result = future.result()
                    results[query_name] = result
                except Exception as e:
                    results[query_name] = {'error': str(e)}
        
        return results
    
    def _execute_single_query(self, query_info: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个查询"""
        start_time = time.time()
        
        with Session(self.engine) as session:
            try:
                if 'raw_sql' in query_info:
                    result = session.execute(text(query_info['raw_sql']))
                    data = result.fetchall()
                else:
                    result = session.exec(query_info['query'])
                    data = result.all()
                
                execution_time = time.time() - start_time
                
                return {
                    'execution_time': execution_time,
                    'row_count': len(data),
                    'data': data[:10] if query_info.get('include_sample') else None  # 只返回前10行作为样本
                }
                
            except Exception as e:
                return {
                    'execution_time': time.time() - start_time,
                    'error': str(e)
                }
    
    def partition_large_query(self, base_query, partition_column: str, 
                            partition_count: int = 4) -> List[Dict[str, Any]]:
        """将大查询分区执行"""
        # 获取分区边界
        with Session(self.engine) as session:
            # 假设是数值分区
            min_max_query = select(
                func.min(getattr(User, partition_column)).label('min_val'),
                func.max(getattr(User, partition_column)).label('max_val')
            )
            result = session.exec(min_max_query).first()
            
            if not result:
                return []
            
            min_val, max_val = result.min_val, result.max_val
            step = (max_val - min_val) / partition_count
            
            # 创建分区查询
            partition_queries = []
            for i in range(partition_count):
                start_val = min_val + i * step
                end_val = min_val + (i + 1) * step if i < partition_count - 1 else max_val
                
                partition_query = base_query.where(
                    getattr(User, partition_column).between(start_val, end_val)
                )
                
                partition_queries.append({
                    'name': f'partition_{i}',
                    'query': partition_query,
                    'range': (start_val, end_val)
                })
            
            return partition_queries

class AsyncQueryOptimizer:
    """异步查询优化器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
    
    async def execute_async_queries(self, queries: List[str]) -> List[Dict[str, Any]]:
        """异步执行多个查询"""
        conn = await asyncpg.connect(self.database_url)
        
        try:
            tasks = []
            for i, query in enumerate(queries):
                task = asyncio.create_task(
                    self._execute_async_query(conn, query, f"query_{i}")
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
            
        finally:
            await conn.close()
    
    async def _execute_async_query(self, conn, query: str, name: str) -> Dict[str, Any]:
        """执行单个异步查询"""
        start_time = time.time()
        
        try:
            result = await conn.fetch(query)
            execution_time = time.time() - start_time
            
            return {
                'name': name,
                'execution_time': execution_time,
                'row_count': len(result),
                'success': True
            }
            
        except Exception as e:
            return {
                'name': name,
                'execution_time': time.time() - start_time,
                'error': str(e),
                'success': False
            }
    
    async def optimize_batch_operations(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """优化批量操作"""
        conn = await asyncpg.connect(self.database_url)
        
        try:
            # 开始事务
            async with conn.transaction():
                results = []
                
                for operation in operations:
                    if operation['type'] == 'insert':
                        result = await self._batch_insert(conn, operation)
                    elif operation['type'] == 'update':
                        result = await self._batch_update(conn, operation)
                    elif operation['type'] == 'delete':
                        result = await self._batch_delete(conn, operation)
                    else:
                        result = {'error': f"Unknown operation type: {operation['type']}"}
                    
                    results.append(result)
                
                return {
                    'total_operations': len(operations),
                    'results': results,
                    'success': all(r.get('success', False) for r in results)
                }
                
        finally:
            await conn.close()
    
    async def _batch_insert(self, conn, operation: Dict[str, Any]) -> Dict[str, Any]:
        """批量插入"""
        start_time = time.time()
        
        try:
            query = operation['query']
            data = operation['data']
            
            # 使用 executemany 进行批量插入
            await conn.executemany(query, data)
            
            return {
                'type': 'insert',
                'execution_time': time.time() - start_time,
                'affected_rows': len(data),
                'success': True
            }
            
        except Exception as e:
            return {
                'type': 'insert',
                'execution_time': time.time() - start_time,
                'error': str(e),
                'success': False
            }
    
    async def _batch_update(self, conn, operation: Dict[str, Any]) -> Dict[str, Any]:
        """批量更新"""
        start_time = time.time()
        
        try:
            query = operation['query']
            data = operation['data']
            
            affected_rows = 0
            for record in data:
                result = await conn.execute(query, *record)
                affected_rows += int(result.split()[-1])  # 提取影响的行数
            
            return {
                'type': 'update',
                'execution_time': time.time() - start_time,
                'affected_rows': affected_rows,
                'success': True
            }
            
        except Exception as e:
            return {
                'type': 'update',
                'execution_time': time.time() - start_time,
                'error': str(e),
                'success': False
            }
    
    async def _batch_delete(self, conn, operation: Dict[str, Any]) -> Dict[str, Any]:
        """批量删除"""
        start_time = time.time()
        
        try:
            query = operation['query']
            params = operation.get('params', [])
            
            result = await conn.execute(query, *params)
            affected_rows = int(result.split()[-1])
            
            return {
                'type': 'delete',
                'execution_time': time.time() - start_time,
                'affected_rows': affected_rows,
                'success': True
            }
            
        except Exception as e:
            return {
                'type': 'delete',
                'execution_time': time.time() - start_time,
                'error': str(e),
                'success': False
            }

# 使用示例
def demonstrate_parallel_optimization():
    """演示并行查询优化"""
    engine = create_engine(
        "postgresql://user:pass@localhost/db",
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20
    )
    
    executor = ParallelQueryExecutor(engine, max_workers=4)
    
    # 定义多个查询
    queries = [
        {
            'name': 'user_stats',
            'query': select(func.count(User.id)).where(User.is_active == True)
        },
        {
            'name': 'post_stats',
            'query': select(func.count(Post.id)).where(Post.is_published == True)
        },
        {
            'name': 'recent_posts',
            'raw_sql': "SELECT * FROM posts WHERE created_at > NOW() - INTERVAL '7 days'",
            'include_sample': True
        }
    ]
    
    # 并行执行
    start_time = time.time()
    results = executor.execute_parallel_queries(queries)
    parallel_time = time.time() - start_time
    
    print(f"并行执行时间: {parallel_time:.3f}s")
    
    # 串行执行对比
    start_time = time.time()
    with Session(engine) as session:
        for query_info in queries:
            if 'raw_sql' in query_info:
                session.execute(text(query_info['raw_sql'])).fetchall()
            else:
                session.exec(query_info['query']).all()
    serial_time = time.time() - start_time
    
    print(f"串行执行时间: {serial_time:.3f}s")
    print(f"性能提升: {(serial_time - parallel_time) / serial_time * 100:.1f}%")
    
    # 分区查询示例
    base_query = select(User).where(User.is_active == True)
    partition_queries = executor.partition_large_query(base_query, 'id', 4)
    
    if partition_queries:
        partition_results = executor.execute_parallel_queries(partition_queries)
        print("\n分区查询结果:")
        for name, result in partition_results.items():
            if 'error' not in result:
                print(f"  {name}: {result['row_count']} rows in {result['execution_time']:.3f}s")

async def demonstrate_async_optimization():
    """演示异步查询优化"""
    optimizer = AsyncQueryOptimizer("postgresql://user:pass@localhost/db")
    
    queries = [
        "SELECT COUNT(*) FROM users WHERE is_active = true",
        "SELECT COUNT(*) FROM posts WHERE is_published = true",
        "SELECT AVG(view_count) FROM posts WHERE created_at > NOW() - INTERVAL '30 days'"
    ]
    
    # 异步执行
    start_time = time.time()
    results = await optimizer.execute_async_queries(queries)
    async_time = time.time() - start_time
    
    print(f"异步执行时间: {async_time:.3f}s")
    
    for result in results:
        if isinstance(result, dict) and result.get('success'):
            print(f"  {result['name']}: {result['execution_time']:.3f}s")
    
    # 批量操作示例
    batch_operations = [
        {
            'type': 'insert',
            'query': 'INSERT INTO logs (message, created_at) VALUES ($1, $2)',
            'data': [('Log message 1', datetime.utcnow()), ('Log message 2', datetime.utcnow())]
        },
        {
            'type': 'update',
            'query': 'UPDATE users SET last_login = $1 WHERE id = $2',
            'data': [(datetime.utcnow(), 1), (datetime.utcnow(), 2)]
        }
    ]
    
    batch_results = await optimizer.optimize_batch_operations(batch_operations)
    print(f"\n批量操作结果: {batch_results['success']}")
    print(f"总操作数: {batch_results['total_operations']}")
```

---

## 5. 缓存策略

### 5.1 查询结果缓存

```python
# query_caching.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import text, func
from typing import Optional, List, Dict, Any, Union, Callable
from datetime import datetime, timedelta
import redis
import json
import hashlib
import pickle
from functools import wraps
import time

class QueryCache:
    """查询缓存管理器"""
    
    def __init__(self, redis_client: redis.Redis, default_ttl: int = 3600):
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'errors': 0
        }
    
    def cache_key(self, query, params: Dict[str, Any] = None) -> str:
        """生成缓存键"""
        # 编译查询为SQL
        compiled_query = query.compile(
            compile_kwargs={"literal_binds": True}
        )
        sql_statement = str(compiled_query)
        
        # 包含参数
        cache_data = {
            'sql': sql_statement,
            'params': params or {}
        }
        
        # 生成哈希
        cache_string = json.dumps(cache_data, sort_keys=True)
        return f"query_cache:{hashlib.md5(cache_string.encode()).hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                self.cache_stats['hits'] += 1
                return pickle.loads(cached_data)
            else:
                self.cache_stats['misses'] += 1
                return None
        except Exception as e:
            self.cache_stats['errors'] += 1
            print(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        try:
            ttl = ttl or self.default_ttl
            serialized_value = pickle.dumps(value)
            result = self.redis.setex(key, ttl, serialized_value)
            if result:
                self.cache_stats['sets'] += 1
            return result
        except Exception as e:
            self.cache_stats['errors'] += 1
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            self.cache_stats['errors'] += 1
            print(f"Cache delete error: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """按模式删除缓存"""
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            self.cache_stats['errors'] += 1
            print(f"Cache invalidate error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.cache_stats,
            'total_requests': total_requests,
            'hit_rate': f"{hit_rate:.2f}%"
        }

class CachedQueryService:
    """缓存查询服务"""
    
    def __init__(self, session: Session, cache: QueryCache):
        self.session = session
        self.cache = cache
    
    def cached_query(self, query, ttl: Optional[int] = None, 
                    cache_key_suffix: str = "") -> List[Any]:
        """执行缓存查询"""
        # 生成缓存键
        cache_key = self.cache.cache_key(query) + cache_key_suffix
        
        # 尝试从缓存获取
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # 执行查询
        start_time = time.time()
        result = self.session.exec(query).all()
        execution_time = time.time() - start_time
        
        # 缓存结果
        self.cache.set(cache_key, result, ttl)
        
        print(f"Query executed in {execution_time:.3f}s and cached")
        return result
    
    def get_user_posts_cached(self, user_id: int, ttl: int = 1800) -> List[Post]:
        """获取用户文章（缓存版本）"""
        query = select(Post).where(
            and_(
                Post.user_id == user_id,
                Post.is_published == True
            )
        ).order_by(Post.created_at.desc())
        
        return self.cached_query(query, ttl, f":user_{user_id}")
    
    def get_popular_posts_cached(self, limit: int = 10, ttl: int = 3600) -> List[Post]:
        """获取热门文章（缓存版本）"""
        query = select(Post).where(
            Post.is_published == True
        ).order_by(
            Post.view_count.desc()
        ).limit(limit)
        
        return self.cached_query(query, ttl, f":popular_{limit}")
    
    def get_user_stats_cached(self, user_id: int, ttl: int = 7200) -> Dict[str, Any]:
        """获取用户统计（缓存版本）"""
        cache_key = f"user_stats:{user_id}"
        
        # 尝试从缓存获取
        cached_stats = self.cache.get(cache_key)
        if cached_stats is not None:
            return cached_stats
        
        # 计算统计数据
        post_count_query = select(func.count(Post.id)).where(
            and_(
                Post.user_id == user_id,
                Post.is_published == True
            )
        )
        
        total_views_query = select(func.sum(Post.view_count)).where(
            and_(
                Post.user_id == user_id,
                Post.is_published == True
            )
        )
        
        post_count = self.session.exec(post_count_query).first() or 0
        total_views = self.session.exec(total_views_query).first() or 0
        
        stats = {
            'user_id': user_id,
            'post_count': post_count,
            'total_views': total_views,
            'avg_views': total_views / post_count if post_count > 0 else 0,
            'calculated_at': datetime.utcnow().isoformat()
        }
        
        # 缓存统计数据
        self.cache.set(cache_key, stats, ttl)
        
        return stats
    
    def invalidate_user_cache(self, user_id: int):
        """使用户相关缓存失效"""
        patterns = [
            f"query_cache:*:user_{user_id}",
            f"user_stats:{user_id}"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = self.cache.invalidate_pattern(pattern)
            total_deleted += deleted
        
        print(f"Invalidated {total_deleted} cache entries for user {user_id}")
        return total_deleted

def cache_decorator(cache: QueryCache, ttl: int = 3600, key_prefix: str = ""):
    """查询缓存装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

class SmartCacheManager:
    """智能缓存管理器"""
    
    def __init__(self, cache: QueryCache):
        self.cache = cache
        self.cache_dependencies = {}  # 缓存依赖关系
        self.access_patterns = {}     # 访问模式统计
    
    def register_dependency(self, cache_key: str, dependencies: List[str]):
        """注册缓存依赖关系"""
        self.cache_dependencies[cache_key] = dependencies
    
    def invalidate_dependent_caches(self, changed_entity: str):
        """使依赖缓存失效"""
        invalidated_keys = []
        
        for cache_key, dependencies in self.cache_dependencies.items():
            if changed_entity in dependencies:
                if self.cache.delete(cache_key):
                    invalidated_keys.append(cache_key)
        
        return invalidated_keys
    
    def track_access(self, cache_key: str):
        """跟踪缓存访问"""
        if cache_key not in self.access_patterns:
            self.access_patterns[cache_key] = {
                'access_count': 0,
                'last_access': None,
                'first_access': datetime.utcnow()
            }
        
        self.access_patterns[cache_key]['access_count'] += 1
        self.access_patterns[cache_key]['last_access'] = datetime.utcnow()
    
    def get_cache_recommendations(self) -> Dict[str, Any]:
        """获取缓存优化建议"""
        recommendations = {
            'hot_keys': [],      # 热点键
            'cold_keys': [],     # 冷键
            'ttl_suggestions': {}  # TTL建议
        }
        
        now = datetime.utcnow()
        
        for cache_key, pattern in self.access_patterns.items():
            access_count = pattern['access_count']
            last_access = pattern['last_access']
            age = (now - pattern['first_access']).total_seconds()
            
            # 计算访问频率
            access_rate = access_count / (age / 3600) if age > 0 else 0  # 每小时访问次数
            
            if access_rate > 10:  # 高频访问
                recommendations['hot_keys'].append({
                    'key': cache_key,
                    'access_rate': access_rate,
                    'suggestion': 'Consider longer TTL or preloading'
                })
            elif access_rate < 0.1:  # 低频访问
                recommendations['cold_keys'].append({
                    'key': cache_key,
                    'access_rate': access_rate,
                    'suggestion': 'Consider shorter TTL or removal'
                })
            
            # TTL建议
            if access_rate > 5:
                suggested_ttl = 7200  # 2小时
            elif access_rate > 1:
                suggested_ttl = 3600  # 1小时
            else:
                suggested_ttl = 1800  # 30分钟
            
            recommendations['ttl_suggestions'][cache_key] = suggested_ttl
        
        return recommendations

# 使用示例
def demonstrate_query_caching():
    """演示查询缓存"""
    # 初始化Redis连接
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    
    # 创建缓存管理器
    cache = QueryCache(redis_client, default_ttl=3600)
    
    # 创建数据库会话
    engine = create_engine("postgresql://user:pass@localhost/db")
    
    with Session(engine) as session:
        # 创建缓存查询服务
        cached_service = CachedQueryService(session, cache)
        
        # 测试缓存查询
        print("第一次查询（从数据库）:")
        start_time = time.time()
        posts = cached_service.get_popular_posts_cached(limit=5)
        first_query_time = time.time() - start_time
        print(f"查询时间: {first_query_time:.3f}s")
        
        print("\n第二次查询（从缓存）:")
        start_time = time.time()
        posts = cached_service.get_popular_posts_cached(limit=5)
        second_query_time = time.time() - start_time
        print(f"查询时间: {second_query_time:.3f}s")
        
        print(f"\n缓存加速: {(first_query_time - second_query_time) / first_query_time * 100:.1f}%")
        
        # 获取缓存统计
        stats = cache.get_stats()
        print(f"\n缓存统计: {stats}")
        
        # 测试用户统计缓存
        user_stats = cached_service.get_user_stats_cached(user_id=1)
        print(f"\n用户统计: {user_stats}")
        
        # 智能缓存管理
        smart_cache = SmartCacheManager(cache)
        
        # 注册依赖关系
        smart_cache.register_dependency("query_cache:popular_posts", ["posts"])
        smart_cache.register_dependency("user_stats:1", ["users", "posts"])
        
        # 模拟数据变更
        invalidated = smart_cache.invalidate_dependent_caches("posts")
        print(f"\n数据变更后失效的缓存: {invalidated}")
        
        # 获取优化建议
        recommendations = smart_cache.get_cache_recommendations()
        print(f"\n缓存优化建议: {recommendations}")

@cache_decorator(cache=QueryCache(redis.Redis()), ttl=1800, key_prefix="user_service")
def get_user_profile(user_id: int) -> Dict[str, Any]:
    """获取用户资料（装饰器缓存）"""
    # 模拟数据库查询
    time.sleep(0.1)  # 模拟查询延迟
    
    return {
         'user_id': user_id,
         'username': f'user_{user_id}',
         'profile_data': 'some profile data',
         'fetched_at': datetime.utcnow().isoformat()
     }
```

### 5.2 应用级缓存

```python
# application_caching.py
from sqlmodel import SQLModel, Field, Session, select
from typing import Optional, List, Dict, Any, TypeVar, Generic
from datetime import datetime, timedelta
import threading
import weakref
from collections import OrderedDict
import time

T = TypeVar('T')

class LRUCache(Generic[T]):
    """LRU缓存实现"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存项"""
        with self.lock:
            if key in self.cache:
                # 移动到末尾（最近使用）
                value = self.cache.pop(key)
                self.cache[key] = value
                self.stats['hits'] += 1
                return value
            else:
                self.stats['misses'] += 1
                return None
    
    def put(self, key: str, value: T) -> None:
        """设置缓存项"""
        with self.lock:
            if key in self.cache:
                # 更新现有项
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                # 移除最久未使用的项
                self.cache.popitem(last=False)
                self.stats['evictions'] += 1
            
            self.cache[key] = value
    
    def remove(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        return len(self.cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate': f"{hit_rate:.2f}%",
            'cache_size': self.size(),
            'max_size': self.max_size
        }

class TTLCache(Generic[T]):
    """带TTL的缓存实现"""
    
    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cache = {}
        self.expiry_times = {}
        self.lock = threading.RLock()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'expired': 0,
            'evictions': 0
        }
    
    def _is_expired(self, key: str) -> bool:
        """检查是否过期"""
        if key not in self.expiry_times:
            return True
        return time.time() > self.expiry_times[key]
    
    def _cleanup_expired(self) -> None:
        """清理过期项"""
        current_time = time.time()
        expired_keys = [
            key for key, expiry_time in self.expiry_times.items()
            if current_time > expiry_time
        ]
        
        for key in expired_keys:
            if key in self.cache:
                del self.cache[key]
            if key in self.expiry_times:
                del self.expiry_times[key]
            self.stats['expired'] += 1
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存项"""
        with self.lock:
            self._cleanup_expired()
            
            if key in self.cache and not self._is_expired(key):
                self.stats['hits'] += 1
                return self.cache[key]
            else:
                self.stats['misses'] += 1
                return None
    
    def put(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """设置缓存项"""
        with self.lock:
            self._cleanup_expired()
            
            # 检查大小限制
            if len(self.cache) >= self.max_size and key not in self.cache:
                # 移除一个项（简单的FIFO策略）
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                if oldest_key in self.expiry_times:
                    del self.expiry_times[oldest_key]
                self.stats['evictions'] += 1
            
            self.cache[key] = value
            ttl = ttl or self.default_ttl
            self.expiry_times[key] = time.time() + ttl
    
    def remove(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            removed = False
            if key in self.cache:
                del self.cache[key]
                removed = True
            if key in self.expiry_times:
                del self.expiry_times[key]
            return removed
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.expiry_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate': f"{hit_rate:.2f}%",
            'cache_size': len(self.cache),
            'max_size': self.max_size
        }

class MultiLevelCache:
    """多级缓存"""
    
    def __init__(self):
        self.l1_cache = LRUCache(max_size=100)  # 内存缓存（小而快）
        self.l2_cache = TTLCache(max_size=1000, default_ttl=3600)  # 应用缓存（大一些）
        self.l3_cache = None  # Redis缓存（可选）
    
    def set_l3_cache(self, redis_cache):
        """设置L3缓存（Redis）"""
        self.l3_cache = redis_cache
    
    def get(self, key: str) -> Optional[Any]:
        """多级获取"""
        # L1缓存
        value = self.l1_cache.get(key)
        if value is not None:
            return value
        
        # L2缓存
        value = self.l2_cache.get(key)
        if value is not None:
            # 回填到L1
            self.l1_cache.put(key, value)
            return value
        
        # L3缓存（Redis）
        if self.l3_cache:
            value = self.l3_cache.get(key)
            if value is not None:
                # 回填到L1和L2
                self.l1_cache.put(key, value)
                self.l2_cache.put(key, value)
                return value
        
        return None
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """多级设置"""
        # 设置到所有级别
        self.l1_cache.put(key, value)
        self.l2_cache.put(key, value, ttl)
        
        if self.l3_cache:
            self.l3_cache.set(key, value, ttl or 3600)
    
    def remove(self, key: str) -> None:
        """多级删除"""
        self.l1_cache.remove(key)
        self.l2_cache.remove(key)
        
        if self.l3_cache:
            self.l3_cache.delete(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            'l1_cache': self.l1_cache.get_stats(),
            'l2_cache': self.l2_cache.get_stats()
        }
        
        if self.l3_cache:
            stats['l3_cache'] = self.l3_cache.get_stats()
        
        return stats

class CacheWarmer:
    """缓存预热器"""
    
    def __init__(self, session: Session, cache: MultiLevelCache):
        self.session = session
        self.cache = cache
    
    def warm_popular_data(self) -> Dict[str, Any]:
        """预热热门数据"""
        start_time = time.time()
        warmed_items = 0
        
        try:
            # 预热热门文章
            popular_posts = self.session.exec(
                select(Post).where(Post.is_published == True)
                .order_by(Post.view_count.desc())
                .limit(50)
            ).all()
            
            for post in popular_posts:
                cache_key = f"post:{post.id}"
                self.cache.put(cache_key, post, ttl=7200)
                warmed_items += 1
            
            # 预热活跃用户
            active_users = self.session.exec(
                select(User).where(User.is_active == True)
                .order_by(User.last_login.desc())
                .limit(100)
            ).all()
            
            for user in active_users:
                cache_key = f"user:{user.id}"
                self.cache.put(cache_key, user, ttl=3600)
                warmed_items += 1
            
            # 预热统计数据
            stats_data = {
                'total_users': self.session.exec(select(func.count(User.id))).first(),
                'total_posts': self.session.exec(select(func.count(Post.id))).first(),
                'active_users': self.session.exec(
                    select(func.count(User.id)).where(User.is_active == True)
                ).first()
            }
            
            self.cache.put("site_stats", stats_data, ttl=1800)
            warmed_items += 1
            
            execution_time = time.time() - start_time
            
            return {
                'success': True,
                'warmed_items': warmed_items,
                'execution_time': execution_time
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'warmed_items': warmed_items,
                'execution_time': time.time() - start_time
            }
    
    def warm_user_data(self, user_id: int) -> Dict[str, Any]:
        """预热特定用户数据"""
        start_time = time.time()
        warmed_items = 0
        
        try:
            # 用户基本信息
            user = self.session.get(User, user_id)
            if user:
                self.cache.put(f"user:{user_id}", user, ttl=3600)
                warmed_items += 1
            
            # 用户文章
            user_posts = self.session.exec(
                select(Post).where(
                    and_(
                        Post.user_id == user_id,
                        Post.is_published == True
                    )
                ).order_by(Post.created_at.desc())
                .limit(20)
            ).all()
            
            self.cache.put(f"user_posts:{user_id}", user_posts, ttl=1800)
            warmed_items += 1
            
            # 用户统计
            user_stats = {
                'post_count': len(user_posts),
                'total_views': sum(post.view_count for post in user_posts),
                'last_post_date': max(post.created_at for post in user_posts) if user_posts else None
            }
            
            self.cache.put(f"user_stats:{user_id}", user_stats, ttl=3600)
            warmed_items += 1
            
            execution_time = time.time() - start_time
            
            return {
                'success': True,
                'user_id': user_id,
                'warmed_items': warmed_items,
                'execution_time': execution_time
            }
            
        except Exception as e:
            return {
                'success': False,
                'user_id': user_id,
                'error': str(e),
                'warmed_items': warmed_items,
                'execution_time': time.time() - start_time
            }

# 使用示例
def demonstrate_application_caching():
    """演示应用级缓存"""
    # 创建多级缓存
    multi_cache = MultiLevelCache()
    
    # 可选：添加Redis作为L3缓存
    # redis_cache = QueryCache(redis.Redis())
    # multi_cache.set_l3_cache(redis_cache)
    
    # 测试缓存性能
    test_data = {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}
    
    # 写入测试
    start_time = time.time()
    for key, value in test_data.items():
        multi_cache.put(key, value)
    write_time = time.time() - start_time
    
    print(f"写入时间: {write_time:.4f}s")
    
    # 读取测试（第一次，从L2/L3）
    start_time = time.time()
    for key in test_data.keys():
        value = multi_cache.get(key)
    first_read_time = time.time() - start_time
    
    print(f"第一次读取时间: {first_read_time:.4f}s")
    
    # 读取测试（第二次，从L1）
    start_time = time.time()
    for key in test_data.keys():
        value = multi_cache.get(key)
    second_read_time = time.time() - start_time
    
    print(f"第二次读取时间: {second_read_time:.4f}s")
    print(f"L1缓存加速: {(first_read_time - second_read_time) / first_read_time * 100:.1f}%")
    
    # 获取统计信息
    stats = multi_cache.get_stats()
    print(f"\n缓存统计: {stats}")
    
    # 测试缓存预热
    engine = create_engine("postgresql://user:pass@localhost/db")
    
    with Session(engine) as session:
        warmer = CacheWarmer(session, multi_cache)
        
        # 预热热门数据
        warm_result = warmer.warm_popular_data()
        print(f"\n预热结果: {warm_result}")
        
        # 预热特定用户数据
        user_warm_result = warmer.warm_user_data(user_id=1)
        print(f"用户预热结果: {user_warm_result}")
```

---

## 6. 性能监控

### 6.1 查询性能监控

```python
# performance_monitoring.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import event, text, func
from sqlalchemy.engine import Engine
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import time
import threading
import statistics
import json

@dataclass
class QueryMetrics:
    """查询指标"""
    sql: str
    execution_time: float
    row_count: int
    timestamp: datetime
    connection_id: Optional[str] = None
    user_id: Optional[int] = None
    endpoint: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

class QueryPerformanceMonitor:
    """查询性能监控器"""
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.query_history = deque(maxlen=max_history)
        self.slow_query_threshold = 1.0  # 1秒
        self.query_stats = defaultdict(list)
        self.lock = threading.RLock()
        
        # 实时统计
        self.current_stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'failed_queries': 0,
            'total_execution_time': 0.0,
            'avg_execution_time': 0.0
        }
    
    def record_query(self, metrics: QueryMetrics) -> None:
        """记录查询指标"""
        with self.lock:
            self.query_history.append(metrics)
            
            # 更新统计
            self.current_stats['total_queries'] += 1
            self.current_stats['total_execution_time'] += metrics.execution_time
            
            if metrics.error:
                self.current_stats['failed_queries'] += 1
            
            if metrics.execution_time > self.slow_query_threshold:
                self.current_stats['slow_queries'] += 1
            
            # 计算平均执行时间
            if self.current_stats['total_queries'] > 0:
                self.current_stats['avg_execution_time'] = (
                    self.current_stats['total_execution_time'] / 
                    self.current_stats['total_queries']
                )
            
            # 按SQL语句分组统计
            sql_key = self._normalize_sql(metrics.sql)
            self.query_stats[sql_key].append(metrics.execution_time)
    
    def _normalize_sql(self, sql: str) -> str:
        """标准化SQL语句（移除参数值）"""
        # 简单的标准化：移除数字和字符串字面量
        import re
        normalized = re.sub(r"'[^']*'", "'?'", sql)
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        return normalized.strip()
    
    def get_slow_queries(self, limit: int = 10) -> List[QueryMetrics]:
        """获取慢查询"""
        with self.lock:
            slow_queries = [
                metrics for metrics in self.query_history
                if metrics.execution_time > self.slow_query_threshold
            ]
            
            # 按执行时间降序排序
            slow_queries.sort(key=lambda x: x.execution_time, reverse=True)
            return slow_queries[:limit]
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """获取查询统计"""
        with self.lock:
            stats = self.current_stats.copy()
            
            # 添加详细统计
            if self.query_history:
                execution_times = [m.execution_time for m in self.query_history if not m.error]
                
                if execution_times:
                    stats.update({
                        'min_execution_time': min(execution_times),
                        'max_execution_time': max(execution_times),
                        'median_execution_time': statistics.median(execution_times),
                        'p95_execution_time': statistics.quantiles(execution_times, n=20)[18],  # 95th percentile
                        'p99_execution_time': statistics.quantiles(execution_times, n=100)[98]  # 99th percentile
                    })
            
            # 错误率
            if stats['total_queries'] > 0:
                stats['error_rate'] = (stats['failed_queries'] / stats['total_queries']) * 100
                stats['slow_query_rate'] = (stats['slow_queries'] / stats['total_queries']) * 100
            
            return stats
    
    def get_top_queries_by_frequency(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最频繁的查询"""
        with self.lock:
            query_frequency = defaultdict(int)
            query_total_time = defaultdict(float)
            
            for metrics in self.query_history:
                sql_key = self._normalize_sql(metrics.sql)
                query_frequency[sql_key] += 1
                query_total_time[sql_key] += metrics.execution_time
            
            # 按频率排序
            top_queries = []
            for sql_key in sorted(query_frequency.keys(), key=lambda x: query_frequency[x], reverse=True)[:limit]:
                avg_time = query_total_time[sql_key] / query_frequency[sql_key]
                top_queries.append({
                    'sql': sql_key,
                    'frequency': query_frequency[sql_key],
                    'total_time': query_total_time[sql_key],
                    'avg_time': avg_time
                })
            
            return top_queries
    
    def get_performance_trends(self, window_minutes: int = 60) -> Dict[str, List[Dict[str, Any]]]:
        """获取性能趋势"""
        with self.lock:
            now = datetime.utcnow()
            window_start = now - timedelta(minutes=window_minutes)
            
            # 过滤时间窗口内的查询
            recent_queries = [
                metrics for metrics in self.query_history
                if metrics.timestamp >= window_start
            ]
            
            # 按分钟分组
            minute_buckets = defaultdict(list)
            for metrics in recent_queries:
                minute_key = metrics.timestamp.replace(second=0, microsecond=0)
                minute_buckets[minute_key].append(metrics)
            
            # 计算每分钟的统计
            trends = {
                'query_count': [],
                'avg_execution_time': [],
                'error_count': []
            }
            
            for minute, queries in sorted(minute_buckets.items()):
                execution_times = [q.execution_time for q in queries if not q.error]
                error_count = sum(1 for q in queries if q.error)
                
                trends['query_count'].append({
                    'timestamp': minute.isoformat(),
                    'value': len(queries)
                })
                
                if execution_times:
                    trends['avg_execution_time'].append({
                        'timestamp': minute.isoformat(),
                        'value': statistics.mean(execution_times)
                    })
                
                trends['error_count'].append({
                    'timestamp': minute.isoformat(),
                    'value': error_count
                })
            
            return trends
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        return {
            'summary': self.get_query_statistics(),
            'slow_queries': self.get_slow_queries(),
            'top_queries': self.get_top_queries_by_frequency(),
            'trends': self.get_performance_trends(),
            'generated_at': datetime.utcnow().isoformat()
        }

class SQLAlchemyMonitoringPlugin:
    """SQLAlchemy监控插件"""
    
    def __init__(self, monitor: QueryPerformanceMonitor):
        self.monitor = monitor
        self.active_queries = {}
    
    def install(self, engine: Engine) -> None:
        """安装监控插件"""
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            context._query_statement = statement
            context._query_parameters = parameters
        
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            execution_time = time.time() - context._query_start_time
            
            metrics = QueryMetrics(
                sql=statement,
                execution_time=execution_time,
                row_count=cursor.rowcount if hasattr(cursor, 'rowcount') else 0,
                timestamp=datetime.utcnow(),
                connection_id=str(id(conn)),
                parameters=parameters if isinstance(parameters, dict) else {}
            )
            
            self.monitor.record_query(metrics)
        
        @event.listens_for(engine, "handle_error")
        def handle_error(exception_context):
            if hasattr(exception_context, '_query_start_time'):
                execution_time = time.time() - exception_context._query_start_time
                
                metrics = QueryMetrics(
                    sql=getattr(exception_context, '_query_statement', 'Unknown'),
                    execution_time=execution_time,
                    row_count=0,
                    timestamp=datetime.utcnow(),
                    error=str(exception_context.original_exception)
                )
                
                self.monitor.record_query(metrics)

class PerformanceAlertManager:
    """性能告警管理器"""
    
    def __init__(self, monitor: QueryPerformanceMonitor):
        self.monitor = monitor
        self.alert_rules = []
        self.alert_handlers = []
    
    def add_alert_rule(self, name: str, condition: Callable[[Dict[str, Any]], bool], 
                      message: str) -> None:
        """添加告警规则"""
        self.alert_rules.append({
            'name': name,
            'condition': condition,
            'message': message
        })
    
    def add_alert_handler(self, handler: Callable[[str, str], None]) -> None:
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    def check_alerts(self) -> List[Dict[str, str]]:
        """检查告警"""
        stats = self.monitor.get_query_statistics()
        triggered_alerts = []
        
        for rule in self.alert_rules:
            if rule['condition'](stats):
                alert = {
                    'name': rule['name'],
                    'message': rule['message'],
                    'timestamp': datetime.utcnow().isoformat(),
                    'stats': stats
                }
                triggered_alerts.append(alert)
                
                # 触发告警处理器
                for handler in self.alert_handlers:
                    try:
                        handler(rule['name'], rule['message'])
                    except Exception as e:
                        print(f"Alert handler error: {e}")
        
        return triggered_alerts

# 使用示例
def demonstrate_performance_monitoring():
    """演示性能监控"""
    # 创建监控器
    monitor = QueryPerformanceMonitor(max_history=5000)
    
    # 创建数据库引擎
    engine = create_engine("postgresql://user:pass@localhost/db")
    
    # 安装监控插件
    plugin = SQLAlchemyMonitoringPlugin(monitor)
    plugin.install(engine)
    
    # 设置告警管理器
    alert_manager = PerformanceAlertManager(monitor)
    
    # 添加告警规则
    alert_manager.add_alert_rule(
        name="High Average Execution Time",
        condition=lambda stats: stats.get('avg_execution_time', 0) > 0.5,
        message="Average query execution time exceeds 500ms"
    )
    
    alert_manager.add_alert_rule(
        name="High Error Rate",
        condition=lambda stats: stats.get('error_rate', 0) > 5.0,
        message="Query error rate exceeds 5%"
    )
    
    alert_manager.add_alert_rule(
        name="Too Many Slow Queries",
        condition=lambda stats: stats.get('slow_query_rate', 0) > 10.0,
        message="Slow query rate exceeds 10%"
    )
    
    # 添加告警处理器
    def log_alert(name: str, message: str):
        print(f"ALERT [{name}]: {message}")
    
    def email_alert(name: str, message: str):
        # 这里可以实现邮件发送逻辑
        print(f"EMAIL ALERT [{name}]: {message}")
    
    alert_manager.add_alert_handler(log_alert)
    alert_manager.add_alert_handler(email_alert)
    
    # 执行一些查询进行测试
    with Session(engine) as session:
        # 正常查询
        users = session.exec(select(User).limit(10)).all()
        
        # 慢查询（模拟）
        session.execute(text("SELECT pg_sleep(1.5)"))  # PostgreSQL
        
        # 复杂查询
        complex_query = select(User).join(Post).where(
            and_(
                User.is_active == True,
                Post.is_published == True
            )
        ).limit(100)
        results = session.exec(complex_query).all()
    
    # 等待一段时间让监控收集数据
    time.sleep(2)
    
    # 获取性能统计
    stats = monitor.get_query_statistics()
    print(f"性能统计: {json.dumps(stats, indent=2)}")
    
    # 获取慢查询
    slow_queries = monitor.get_slow_queries(limit=5)
    print(f"\n慢查询数量: {len(slow_queries)}")
    for query in slow_queries:
        print(f"  SQL: {query.sql[:100]}...")
        print(f"  执行时间: {query.execution_time:.3f}s")
    
    # 获取热门查询
    top_queries = monitor.get_top_queries_by_frequency(limit=5)
    print(f"\n热门查询:")
    for query in top_queries:
        print(f"  频率: {query['frequency']}, 平均时间: {query['avg_time']:.3f}s")
        print(f"  SQL: {query['sql'][:100]}...")
    
    # 检查告警
    alerts = alert_manager.check_alerts()
    if alerts:
        print(f"\n触发的告警: {len(alerts)}")
        for alert in alerts:
            print(f"  {alert['name']}: {alert['message']}")
    
    # 生成完整报告
     report = monitor.generate_performance_report()
     print(f"\n性能报告已生成，包含 {len(report['slow_queries'])} 个慢查询")
```

### 6.2 系统资源监控

```python
# system_monitoring.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import text
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import psutil
import threading
import time
import json

@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_available: int
    disk_usage_percent: float
    disk_free: int
    active_connections: int
    database_size: Optional[int] = None
    cache_hit_ratio: Optional[float] = None

class SystemResourceMonitor:
    """系统资源监控器"""
    
    def __init__(self, session: Session, check_interval: int = 60):
        self.session = session
        self.check_interval = check_interval
        self.metrics_history = []
        self.max_history = 1440  # 24小时的分钟数
        self.monitoring = False
        self.monitor_thread = None
        
        # 告警阈值
        self.thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'active_connections': 100
        }
    
    def get_system_metrics(self) -> SystemMetrics:
        """获取当前系统指标"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用情况
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available = memory.available
        
        # 磁盘使用情况
        disk = psutil.disk_usage('/')
        disk_usage_percent = (disk.used / disk.total) * 100
        disk_free = disk.free
        
        # 数据库连接数
        active_connections = self._get_active_connections()
        
        # 数据库大小
        database_size = self._get_database_size()
        
        # 缓存命中率
        cache_hit_ratio = self._get_cache_hit_ratio()
        
        return SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_available=memory_available,
            disk_usage_percent=disk_usage_percent,
            disk_free=disk_free,
            active_connections=active_connections,
            database_size=database_size,
            cache_hit_ratio=cache_hit_ratio
        )
    
    def _get_active_connections(self) -> int:
        """获取活跃连接数"""
        try:
            # PostgreSQL
            result = self.session.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            ).scalar()
            return result or 0
        except Exception:
            try:
                # MySQL
                result = self.session.execute(
                    text("SHOW STATUS LIKE 'Threads_connected'")
                ).fetchone()
                return int(result[1]) if result else 0
            except Exception:
                return 0
    
    def _get_database_size(self) -> Optional[int]:
        """获取数据库大小（字节）"""
        try:
            # PostgreSQL
            result = self.session.execute(
                text("SELECT pg_database_size(current_database())")
            ).scalar()
            return result
        except Exception:
            try:
                # MySQL
                result = self.session.execute(
                    text("""
                    SELECT SUM(data_length + index_length) 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE()
                    """)
                ).scalar()
                return result
            except Exception:
                return None
    
    def _get_cache_hit_ratio(self) -> Optional[float]:
        """获取缓存命中率"""
        try:
            # PostgreSQL
            result = self.session.execute(
                text("""
                SELECT 
                    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) * 100 
                FROM pg_statio_user_tables
                """)
            ).scalar()
            return float(result) if result else None
        except Exception:
            return None
    
    def start_monitoring(self) -> None:
        """开始监控"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self) -> None:
        """监控循环"""
        while self.monitoring:
            try:
                metrics = self.get_system_metrics()
                self.metrics_history.append(metrics)
                
                # 保持历史记录在限制范围内
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history.pop(0)
                
                # 检查告警
                self._check_alerts(metrics)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(self.check_interval)
    
    def _check_alerts(self, metrics: SystemMetrics) -> None:
        """检查告警条件"""
        alerts = []
        
        if metrics.cpu_percent > self.thresholds['cpu_percent']:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
        
        if metrics.memory_percent > self.thresholds['memory_percent']:
            alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")
        
        if metrics.disk_usage_percent > self.thresholds['disk_usage_percent']:
            alerts.append(f"High disk usage: {metrics.disk_usage_percent:.1f}%")
        
        if metrics.active_connections > self.thresholds['active_connections']:
            alerts.append(f"High connection count: {metrics.active_connections}")
        
        for alert in alerts:
            print(f"SYSTEM ALERT: {alert}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        if not self.metrics_history:
            return {'status': 'No data available'}
        
        latest = self.metrics_history[-1]
        
        return {
            'timestamp': latest.timestamp.isoformat(),
            'cpu_percent': latest.cpu_percent,
            'memory_percent': latest.memory_percent,
            'memory_available_gb': latest.memory_available / (1024**3),
            'disk_usage_percent': latest.disk_usage_percent,
            'disk_free_gb': latest.disk_free / (1024**3),
            'active_connections': latest.active_connections,
            'database_size_mb': latest.database_size / (1024**2) if latest.database_size else None,
            'cache_hit_ratio': latest.cache_hit_ratio
        }
    
    def get_performance_trends(self, hours: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """获取性能趋势"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= cutoff_time
        ]
        
        trends = {
            'cpu_percent': [],
            'memory_percent': [],
            'disk_usage_percent': [],
            'active_connections': [],
            'cache_hit_ratio': []
        }
        
        for metrics in recent_metrics:
            timestamp = metrics.timestamp.isoformat()
            
            trends['cpu_percent'].append({
                'timestamp': timestamp,
                'value': metrics.cpu_percent
            })
            
            trends['memory_percent'].append({
                'timestamp': timestamp,
                'value': metrics.memory_percent
            })
            
            trends['disk_usage_percent'].append({
                'timestamp': timestamp,
                'value': metrics.disk_usage_percent
            })
            
            trends['active_connections'].append({
                'timestamp': timestamp,
                'value': metrics.active_connections
            })
            
            if metrics.cache_hit_ratio is not None:
                trends['cache_hit_ratio'].append({
                    'timestamp': timestamp,
                    'value': metrics.cache_hit_ratio
                })
        
        return trends
    
    def generate_health_report(self) -> Dict[str, Any]:
        """生成健康报告"""
        if not self.metrics_history:
            return {'status': 'No data available'}
        
        # 最近1小时的数据
        recent_hour = datetime.utcnow() - timedelta(hours=1)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp >= recent_hour
        ]
        
        if not recent_metrics:
            return {'status': 'No recent data available'}
        
        # 计算平均值
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_connections = sum(m.active_connections for m in recent_metrics) / len(recent_metrics)
        
        # 最新数据
        latest = recent_metrics[-1]
        
        # 健康评分（0-100）
        health_score = 100
        
        if avg_cpu > 70:
            health_score -= 20
        elif avg_cpu > 50:
            health_score -= 10
        
        if avg_memory > 80:
            health_score -= 25
        elif avg_memory > 60:
            health_score -= 10
        
        if latest.disk_usage_percent > 85:
            health_score -= 20
        elif latest.disk_usage_percent > 70:
            health_score -= 10
        
        if avg_connections > 80:
            health_score -= 15
        
        # 健康状态
        if health_score >= 80:
            health_status = 'Excellent'
        elif health_score >= 60:
            health_status = 'Good'
        elif health_score >= 40:
            health_status = 'Warning'
        else:
            health_status = 'Critical'
        
        return {
            'health_score': max(0, health_score),
            'health_status': health_status,
            'current_metrics': self.get_current_status(),
            'averages_last_hour': {
                'cpu_percent': avg_cpu,
                'memory_percent': avg_memory,
                'active_connections': avg_connections
            },
            'recommendations': self._get_recommendations(latest, avg_cpu, avg_memory),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _get_recommendations(self, latest: SystemMetrics, avg_cpu: float, avg_memory: float) -> List[str]:
        """获取优化建议"""
        recommendations = []
        
        if avg_cpu > 70:
            recommendations.append("考虑优化CPU密集型查询或增加CPU资源")
        
        if avg_memory > 80:
            recommendations.append("内存使用率较高，考虑增加内存或优化内存使用")
        
        if latest.disk_usage_percent > 85:
            recommendations.append("磁盘空间不足，需要清理或扩容")
        
        if latest.active_connections > 80:
            recommendations.append("数据库连接数较高，检查连接池配置")
        
        if latest.cache_hit_ratio and latest.cache_hit_ratio < 90:
            recommendations.append("缓存命中率较低，考虑优化查询或增加缓存")
        
        if not recommendations:
            recommendations.append("系统运行良好，继续保持当前配置")
        
        return recommendations

# 使用示例
def demonstrate_system_monitoring():
    """演示系统监控"""
    engine = create_engine("postgresql://user:pass@localhost/db")
    
    with Session(engine) as session:
        # 创建系统监控器
        monitor = SystemResourceMonitor(session, check_interval=30)
        
        # 获取当前指标
        current_metrics = monitor.get_system_metrics()
        print(f"当前系统指标:")
        print(f"  CPU: {current_metrics.cpu_percent:.1f}%")
        print(f"  内存: {current_metrics.memory_percent:.1f}%")
        print(f"  磁盘: {current_metrics.disk_usage_percent:.1f}%")
        print(f"  活跃连接: {current_metrics.active_connections}")
        
        # 开始监控
        monitor.start_monitoring()
        print("\n开始系统监控...")
        
        # 运行一段时间
        time.sleep(120)  # 监控2分钟
        
        # 获取状态报告
        status = monitor.get_current_status()
        print(f"\n当前状态: {json.dumps(status, indent=2)}")
        
        # 生成健康报告
        health_report = monitor.generate_health_report()
        print(f"\n健康报告: {json.dumps(health_report, indent=2)}")
        
        # 停止监控
        monitor.stop_monitoring()
        print("\n监控已停止")
```

---

## 7. 问题诊断与解决

### 7.1 性能问题诊断工具

```python
# performance_diagnostics.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import text, func, and_, or_
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import re
import time

@dataclass
class DiagnosticResult:
    """诊断结果"""
    category: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    issue: str
    description: str
    recommendations: List[str]
    sql_examples: List[str] = None
    metrics: Dict[str, Any] = None

class PerformanceDiagnostics:
    """性能诊断工具"""
    
    def __init__(self, session: Session):
        self.session = session
        self.results = []
    
    def run_full_diagnosis(self) -> List[DiagnosticResult]:
        """运行完整诊断"""
        self.results = []
        
        # 运行各种诊断检查
        self._check_slow_queries()
        self._check_missing_indexes()
        self._check_table_statistics()
        self._check_connection_issues()
        self._check_lock_contention()
        self._check_query_patterns()
        self._check_database_configuration()
        
        return self.results
    
    def _check_slow_queries(self) -> None:
        """检查慢查询"""
        try:
            # PostgreSQL慢查询检查
            slow_queries = self.session.execute(
                text("""
                SELECT query, calls, total_time, mean_time, rows
                FROM pg_stat_statements 
                WHERE mean_time > 1000  -- 超过1秒
                ORDER BY mean_time DESC 
                LIMIT 10
                """)
            ).fetchall()
            
            if slow_queries:
                for query_info in slow_queries:
                    self.results.append(DiagnosticResult(
                        category="Query Performance",
                        severity="high" if query_info.mean_time > 5000 else "medium",
                        issue="Slow Query Detected",
                        description=f"Query with average execution time of {query_info.mean_time:.2f}ms",
                        recommendations=[
                            "分析查询执行计划",
                            "检查是否缺少索引",
                            "考虑查询重写",
                            "检查表统计信息是否过期"
                        ],
                        sql_examples=[query_info.query[:200] + "..."],
                        metrics={
                            "calls": query_info.calls,
                            "total_time": query_info.total_time,
                            "mean_time": query_info.mean_time,
                            "rows": query_info.rows
                        }
                    ))
        except Exception as e:
            print(f"慢查询检查失败: {e}")
    
    def _check_missing_indexes(self) -> None:
        """检查缺失的索引"""
        try:
            # 检查经常进行顺序扫描的表
            seq_scans = self.session.execute(
                text("""
                SELECT schemaname, tablename, seq_scan, seq_tup_read,
                       idx_scan, idx_tup_fetch,
                       seq_tup_read / seq_scan as avg_seq_read
                FROM pg_stat_user_tables 
                WHERE seq_scan > 0
                  AND seq_tup_read / seq_scan > 10000  -- 平均每次扫描超过1万行
                ORDER BY seq_tup_read DESC
                LIMIT 10
                """)
            ).fetchall()
            
            for table_info in seq_scans:
                self.results.append(DiagnosticResult(
                    category="Index Optimization",
                    severity="medium",
                    issue="Potential Missing Index",
                    description=f"Table {table_info.tablename} has high sequential scan ratio",
                    recommendations=[
                        f"分析表 {table_info.tablename} 的查询模式",
                        "考虑在经常用于WHERE条件的列上创建索引",
                        "检查现有索引的使用情况",
                        "考虑创建复合索引"
                    ],
                    metrics={
                        "seq_scan": table_info.seq_scan,
                        "seq_tup_read": table_info.seq_tup_read,
                        "avg_seq_read": table_info.avg_seq_read,
                        "idx_scan": table_info.idx_scan
                    }
                ))
        except Exception as e:
            print(f"索引检查失败: {e}")
    
    def _check_table_statistics(self) -> None:
        """检查表统计信息"""
        try:
            # 检查统计信息过期的表
            stale_stats = self.session.execute(
                text("""
                SELECT schemaname, tablename, last_analyze, last_autoanalyze,
                       n_tup_ins + n_tup_upd + n_tup_del as total_changes
                FROM pg_stat_user_tables 
                WHERE (last_analyze IS NULL OR last_analyze < NOW() - INTERVAL '7 days')
                   AND (last_autoanalyze IS NULL OR last_autoanalyze < NOW() - INTERVAL '7 days')
                   AND (n_tup_ins + n_tup_upd + n_tup_del) > 1000
                ORDER BY total_changes DESC
                """)
            ).fetchall()
            
            for table_info in stale_stats:
                self.results.append(DiagnosticResult(
                    category="Database Maintenance",
                    severity="medium",
                    issue="Stale Table Statistics",
                    description=f"Table {table_info.tablename} has outdated statistics",
                    recommendations=[
                        f"运行 ANALYZE {table_info.tablename}",
                        "考虑调整autovacuum设置",
                        "定期更新表统计信息"
                    ],
                    sql_examples=[f"ANALYZE {table_info.tablename};"],
                    metrics={
                        "last_analyze": str(table_info.last_analyze),
                        "last_autoanalyze": str(table_info.last_autoanalyze),
                        "total_changes": table_info.total_changes
                    }
                ))
        except Exception as e:
            print(f"统计信息检查失败: {e}")
    
    def _check_connection_issues(self) -> None:
        """检查连接问题"""
        try:
            # 检查连接数
            connection_stats = self.session.execute(
                text("""
                SELECT count(*) as total_connections,
                       count(*) FILTER (WHERE state = 'active') as active_connections,
                       count(*) FILTER (WHERE state = 'idle') as idle_connections,
                       count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                FROM pg_stat_activity
                """)
            ).fetchone()
            
            max_connections = self.session.execute(
                text("SHOW max_connections")
            ).scalar()
            
            connection_usage = (connection_stats.total_connections / int(max_connections)) * 100
            
            if connection_usage > 80:
                self.results.append(DiagnosticResult(
                    category="Connection Management",
                    severity="high" if connection_usage > 90 else "medium",
                    issue="High Connection Usage",
                    description=f"Connection usage at {connection_usage:.1f}%",
                    recommendations=[
                        "检查应用程序的连接池配置",
                        "查找长时间运行的连接",
                        "考虑增加max_connections",
                        "优化连接管理策略"
                    ],
                    metrics={
                        "total_connections": connection_stats.total_connections,
                        "active_connections": connection_stats.active_connections,
                        "idle_connections": connection_stats.idle_connections,
                        "idle_in_transaction": connection_stats.idle_in_transaction,
                        "max_connections": int(max_connections),
                        "usage_percent": connection_usage
                    }
                ))
            
            # 检查长时间空闲的事务
            if connection_stats.idle_in_transaction > 5:
                self.results.append(DiagnosticResult(
                    category="Transaction Management",
                    severity="medium",
                    issue="Idle Transactions",
                    description=f"{connection_stats.idle_in_transaction} connections idle in transaction",
                    recommendations=[
                        "检查应用程序的事务管理",
                        "设置idle_in_transaction_session_timeout",
                        "优化事务边界"
                    ],
                    metrics={
                        "idle_in_transaction": connection_stats.idle_in_transaction
                    }
                ))
                
        except Exception as e:
            print(f"连接检查失败: {e}")
    
    def _check_lock_contention(self) -> None:
        """检查锁争用"""
        try:
            # 检查当前锁等待
            lock_waits = self.session.execute(
                text("""
                SELECT blocked_locks.pid AS blocked_pid,
                       blocked_activity.usename AS blocked_user,
                       blocking_locks.pid AS blocking_pid,
                       blocking_activity.usename AS blocking_user,
                       blocked_activity.query AS blocked_statement,
                       blocking_activity.query AS current_statement_in_blocking_process
                FROM pg_catalog.pg_locks blocked_locks
                JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
                JOIN pg_catalog.pg_locks blocking_locks 
                    ON blocking_locks.locktype = blocked_locks.locktype
                    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
                    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
                    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
                    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
                    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
                    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
                    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
                    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
                    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
                    AND blocking_locks.pid != blocked_locks.pid
                JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
                WHERE NOT blocked_locks.granted
                """)
            ).fetchall()
            
            if lock_waits:
                self.results.append(DiagnosticResult(
                    category="Lock Contention",
                    severity="high",
                    issue="Lock Contention Detected",
                    description=f"{len(lock_waits)} queries are waiting for locks",
                    recommendations=[
                        "分析锁等待的查询模式",
                        "优化事务大小和持续时间",
                        "考虑调整锁超时设置",
                        "检查是否有死锁"
                    ],
                    metrics={
                        "waiting_queries": len(lock_waits)
                    }
                ))
                
        except Exception as e:
            print(f"锁检查失败: {e}")
    
    def _check_query_patterns(self) -> None:
        """检查查询模式"""
        try:
            # 检查N+1查询模式（简化版）
            frequent_similar_queries = self.session.execute(
                text("""
                SELECT query, calls
                FROM pg_stat_statements 
                WHERE calls > 100
                  AND query LIKE '%SELECT%FROM%WHERE%=%'
                  AND query NOT LIKE '%LIMIT%'
                ORDER BY calls DESC
                LIMIT 10
                """)
            ).fetchall()
            
            for query_info in frequent_similar_queries:
                if query_info.calls > 1000:
                    self.results.append(DiagnosticResult(
                        category="Query Patterns",
                        severity="medium",
                        issue="Potential N+1 Query Pattern",
                        description=f"Query executed {query_info.calls} times, possible N+1 pattern",
                        recommendations=[
                            "检查是否存在N+1查询问题",
                            "考虑使用JOIN或预加载",
                            "批量查询优化",
                            "使用查询缓存"
                        ],
                        sql_examples=[query_info.query[:200] + "..."],
                        metrics={
                            "calls": query_info.calls
                        }
                    ))
                    
        except Exception as e:
            print(f"查询模式检查失败: {e}")
    
    def _check_database_configuration(self) -> None:
        """检查数据库配置"""
        try:
            # 检查关键配置参数
            config_checks = [
                ('shared_buffers', 'memory'),
                ('effective_cache_size', 'memory'),
                ('work_mem', 'memory'),
                ('maintenance_work_mem', 'memory'),
                ('checkpoint_completion_target', 'float'),
                ('wal_buffers', 'memory')
            ]
            
            for param_name, param_type in config_checks:
                try:
                    value = self.session.execute(
                        text(f"SHOW {param_name}")
                    ).scalar()
                    
                    # 简单的配置检查逻辑
                    if param_name == 'shared_buffers' and 'MB' in value:
                        size_mb = int(value.replace('MB', ''))
                        if size_mb < 256:
                            self.results.append(DiagnosticResult(
                                category="Database Configuration",
                                severity="medium",
                                issue="Low shared_buffers",
                                description=f"shared_buffers is set to {value}, consider increasing",
                                recommendations=[
                                    "增加shared_buffers到系统内存的25%",
                                    "重启数据库以应用更改"
                                ],
                                metrics={"current_value": value}
                            ))
                            
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"配置检查失败: {e}")
    
    def generate_diagnostic_report(self) -> Dict[str, Any]:
        """生成诊断报告"""
        if not self.results:
            self.run_full_diagnosis()
        
        # 按严重程度分组
        by_severity = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }
        
        for result in self.results:
            by_severity[result.severity].append(result)
        
        # 按类别分组
        by_category = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = []
            by_category[result.category].append(result)
        
        # 计算总体健康评分
        total_score = 100
        for result in self.results:
            if result.severity == 'critical':
                total_score -= 25
            elif result.severity == 'high':
                total_score -= 15
            elif result.severity == 'medium':
                total_score -= 8
            elif result.severity == 'low':
                total_score -= 3
        
        total_score = max(0, total_score)
        
        return {
            'overall_score': total_score,
            'total_issues': len(self.results),
            'by_severity': {
                severity: len(issues) for severity, issues in by_severity.items()
            },
            'by_category': {
                category: len(issues) for category, issues in by_category.items()
            },
            'critical_issues': [self._result_to_dict(r) for r in by_severity['critical']],
            'high_priority_issues': [self._result_to_dict(r) for r in by_severity['high']],
            'recommendations': self._get_top_recommendations(),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _result_to_dict(self, result: DiagnosticResult) -> Dict[str, Any]:
        """将诊断结果转换为字典"""
        return {
            'category': result.category,
            'severity': result.severity,
            'issue': result.issue,
            'description': result.description,
            'recommendations': result.recommendations,
            'sql_examples': result.sql_examples,
            'metrics': result.metrics
        }
    
    def _get_top_recommendations(self) -> List[str]:
        """获取最重要的建议"""
        recommendations = []
        
        # 收集所有高优先级问题的建议
        for result in self.results:
            if result.severity in ['critical', 'high']:
                recommendations.extend(result.recommendations)
        
        # 去重并返回前10个
        unique_recommendations = list(dict.fromkeys(recommendations))
        return unique_recommendations[:10]

# 使用示例
def demonstrate_performance_diagnostics():
    """演示性能诊断"""
    engine = create_engine("postgresql://user:pass@localhost/db")
    
    with Session(engine) as session:
        # 创建诊断工具
        diagnostics = PerformanceDiagnostics(session)
        
        # 运行完整诊断
        print("运行性能诊断...")
        results = diagnostics.run_full_diagnosis()
        
        print(f"\n发现 {len(results)} 个问题:")
        for result in results:
            print(f"\n[{result.severity.upper()}] {result.category}: {result.issue}")
            print(f"  描述: {result.description}")
            print(f"  建议: {', '.join(result.recommendations[:2])}")
        
        # 生成完整报告
        report = diagnostics.generate_diagnostic_report()
        print(f"\n诊断报告:")
        print(f"  总体评分: {report['overall_score']}/100")
        print(f"  问题总数: {report['total_issues']}")
        print(f"  严重程度分布: {report['by_severity']}")
        print(f"  类别分布: {report['by_category']}")
        
        if report['critical_issues']:
            print(f"\n关键问题:")
            for issue in report['critical_issues']:
                print(f"  - {issue['issue']}: {issue['description']}")
        
        print(f"\n主要建议:")
         for i, rec in enumerate(report['recommendations'][:5], 1):
             print(f"  {i}. {rec}")
```

### 7.2 常见问题解决方案

```python
# common_solutions.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import text, create_engine
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

class CommonPerformanceSolutions:
    """常见性能问题解决方案"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def fix_n_plus_one_queries(self, table_name: str, relationship_name: str) -> Dict[str, str]:
        """解决N+1查询问题"""
        solutions = {
            "问题描述": "N+1查询问题：执行1个查询获取主记录，然后为每个主记录执行额外查询",
            "解决方案1_预加载": f"""
# 使用selectinload预加载关联数据
from sqlalchemy.orm import selectinload

results = session.exec(
    select(YourModel)
    .options(selectinload(YourModel.{relationship_name}))
).all()
            """,
            "解决方案2_JOIN查询": f"""
# 使用JOIN一次性获取所有数据
results = session.exec(
    select(YourModel, RelatedModel)
    .join(RelatedModel)
).all()
            """,
            "解决方案3_批量查询": f"""
# 批量获取关联数据
ids = [item.id for item in main_items]
related_items = session.exec(
    select(RelatedModel)
    .where(RelatedModel.main_id.in_(ids))
).all()
            """
        }
        return solutions
    
    def optimize_slow_query(self, query: str) -> Dict[str, Any]:
        """优化慢查询"""
        # 分析查询执行计划
        explain_result = self.session.execute(
            text(f"EXPLAIN (ANALYZE, BUFFERS) {query}")
        ).fetchall()
        
        optimization_tips = {
            "执行计划分析": [str(row[0]) for row in explain_result],
            "优化建议": [
                "检查WHERE子句中的列是否有索引",
                "避免在WHERE子句中使用函数",
                "考虑重写子查询为JOIN",
                "检查是否可以添加LIMIT子句",
                "确保统计信息是最新的"
            ],
            "索引建议": self._suggest_indexes_for_query(query),
            "查询重写建议": self._suggest_query_rewrite(query)
        }
        
        return optimization_tips
    
    def _suggest_indexes_for_query(self, query: str) -> List[str]:
        """为查询建议索引"""
        suggestions = []
        
        # 简单的模式匹配来识别可能需要索引的列
        import re
        
        # 查找WHERE条件中的列
        where_patterns = re.findall(r'WHERE\s+([\w.]+)\s*[=<>]', query, re.IGNORECASE)
        for column in where_patterns:
            suggestions.append(f"CREATE INDEX idx_{column.replace('.', '_')} ON table_name ({column});")
        
        # 查找ORDER BY中的列
        order_patterns = re.findall(r'ORDER\s+BY\s+([\w.]+)', query, re.IGNORECASE)
        for column in order_patterns:
            suggestions.append(f"CREATE INDEX idx_{column.replace('.', '_')}_order ON table_name ({column});")
        
        # 查找JOIN条件中的列
        join_patterns = re.findall(r'JOIN\s+\w+\s+ON\s+([\w.]+)\s*=\s*([\w.]+)', query, re.IGNORECASE)
        for left_col, right_col in join_patterns:
            suggestions.append(f"CREATE INDEX idx_{left_col.replace('.', '_')}_join ON table_name ({left_col});")
            suggestions.append(f"CREATE INDEX idx_{right_col.replace('.', '_')}_join ON table_name ({right_col});")
        
        return list(set(suggestions))  # 去重
    
    def _suggest_query_rewrite(self, query: str) -> List[str]:
        """建议查询重写"""
        suggestions = []
        
        if "EXISTS" in query.upper():
            suggestions.append("考虑将EXISTS子查询重写为JOIN")
        
        if "IN (SELECT" in query.upper():
            suggestions.append("考虑将IN子查询重写为JOIN或EXISTS")
        
        if "DISTINCT" in query.upper():
            suggestions.append("检查是否真的需要DISTINCT，考虑使用GROUP BY")
        
        if "LIKE '%" in query.upper():
            suggestions.append("避免以通配符开头的LIKE查询，考虑全文搜索")
        
        return suggestions
    
    def fix_connection_pool_issues(self) -> Dict[str, str]:
        """解决连接池问题"""
        return {
            "问题1_连接泄漏": """
# 确保正确关闭连接
with Session(engine) as session:
    # 使用with语句自动管理连接
    result = session.exec(select(Model)).all()
    # 连接会自动关闭
            """,
            "问题2_连接池配置": """
# 优化连接池配置
engine = create_engine(
    "postgresql://user:pass@localhost/db",
    pool_size=20,          # 连接池大小
    max_overflow=30,       # 最大溢出连接
    pool_timeout=30,       # 获取连接超时
    pool_recycle=3600,     # 连接回收时间
    pool_pre_ping=True     # 连接前ping测试
)
            """,
            "问题3_长连接管理": """
# 避免长时间持有连接
def process_large_dataset():
    with Session(engine) as session:
        # 分批处理大数据集
        offset = 0
        batch_size = 1000
        
        while True:
            batch = session.exec(
                select(Model)
                .offset(offset)
                .limit(batch_size)
            ).all()
            
            if not batch:
                break
                
            # 处理批次数据
            process_batch(batch)
            offset += batch_size
            
            # 提交并释放连接
            session.commit()
            """
        }
    
    def fix_memory_issues(self) -> Dict[str, str]:
        """解决内存问题"""
        return {
            "问题1_大结果集": """
# 使用流式查询处理大结果集
def stream_large_results():
    with Session(engine) as session:
        # 使用yield_per进行流式处理
        query = select(Model).execution_options(stream_results=True)
        
        for row in session.exec(query).yield_per(1000):
            # 逐行处理，避免一次性加载所有数据
            process_row(row)
            """,
            "问题2_预加载优化": """
# 选择性预加载，避免加载不需要的数据
from sqlalchemy.orm import selectinload, joinedload

# 只加载需要的关联数据
results = session.exec(
    select(User)
    .options(
        selectinload(User.orders).selectinload(Order.items),
        # 不加载不需要的关联
        # selectinload(User.profile)  # 如果不需要就不加载
    )
).all()
            """,
            "问题3_批量操作优化": """
# 使用bulk操作减少内存使用
from sqlalchemy import insert, update, delete

# 批量插入
session.execute(
    insert(Model),
    [
        {"name": f"item_{i}", "value": i}
        for i in range(10000)
    ]
)

# 批量更新
session.execute(
    update(Model)
    .where(Model.status == "pending")
    .values(status="processed")
)
            """
        }
    
    def fix_index_issues(self) -> Dict[str, str]:
        """解决索引问题"""
        return {
            "问题1_缺失索引": """
# 为经常查询的列创建索引
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_order_status ON orders(status);
CREATE INDEX idx_order_created_at ON orders(created_at);
            """,
            "问题2_复合索引优化": """
# 创建复合索引，注意列的顺序
# 将选择性高的列放在前面
CREATE INDEX idx_order_status_date ON orders(status, created_at);
CREATE INDEX idx_user_active_email ON users(is_active, email);
            """,
            "问题3_部分索引": """
# 为特定条件创建部分索引
CREATE INDEX idx_active_users ON users(email) 
WHERE is_active = true;

CREATE INDEX idx_recent_orders ON orders(created_at) 
WHERE created_at > '2024-01-01';
            """,
            "问题4_函数索引": """
# 为函数表达式创建索引
CREATE INDEX idx_user_email_lower ON users(LOWER(email));
CREATE INDEX idx_order_year ON orders(EXTRACT(YEAR FROM created_at));
            """
        }

# 使用示例
def demonstrate_common_solutions():
    """演示常见问题解决方案"""
    engine = create_engine("postgresql://user:pass@localhost/db")
    
    with Session(engine) as session:
        solutions = CommonPerformanceSolutions(session)
        
        # N+1查询解决方案
        n_plus_one_solutions = solutions.fix_n_plus_one_queries("users", "orders")
        print("N+1查询解决方案:")
        for key, value in n_plus_one_solutions.items():
            print(f"\n{key}:")
            print(value)
        
        # 慢查询优化
        slow_query = "SELECT * FROM users WHERE email LIKE '%@example.com' ORDER BY created_at"
        optimization = solutions.optimize_slow_query(slow_query)
        print(f"\n慢查询优化建议:")
        print(json.dumps(optimization, indent=2, ensure_ascii=False))
        
        # 连接池问题解决
        connection_solutions = solutions.fix_connection_pool_issues()
        print(f"\n连接池问题解决方案:")
        for key, value in connection_solutions.items():
            print(f"\n{key}:")
            print(value)
        
        # 内存问题解决
        memory_solutions = solutions.fix_memory_issues()
        print(f"\n内存问题解决方案:")
        for key, value in memory_solutions.items():
            print(f"\n{key}:")
            print(value)
        
        # 索引问题解决
        index_solutions = solutions.fix_index_issues()
        print(f"\n索引问题解决方案:")
        for key, value in index_solutions.items():
            print(f"\n{key}:")
            print(value)
```

---

## 8. 最佳实践

### 8.1 查询优化最佳实践

```python
# query_best_practices.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import func, and_, or_, text
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

class QueryBestPractices:
    """查询优化最佳实践"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def efficient_pagination(self, model_class, page: int, page_size: int, 
                           order_column=None) -> Dict[str, Any]:
        """高效分页查询"""
        # 使用偏移量分页（适合小偏移量）
        if page * page_size < 10000:
            offset = (page - 1) * page_size
            
            query = select(model_class)
            if order_column:
                query = query.order_by(order_column)
            
            items = self.session.exec(
                query.offset(offset).limit(page_size)
            ).all()
            
            # 获取总数（可以缓存）
            total = self.session.exec(
                select(func.count()).select_from(model_class)
            ).one()
            
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        
        # 使用游标分页（适合大偏移量）
        else:
            return self._cursor_pagination(model_class, page_size, order_column)
    
    def _cursor_pagination(self, model_class, page_size: int, 
                          order_column, cursor=None) -> Dict[str, Any]:
        """游标分页"""
        query = select(model_class)
        
        if order_column:
            query = query.order_by(order_column)
            
            if cursor:
                # 使用游标继续查询
                query = query.where(order_column > cursor)
        
        items = self.session.exec(query.limit(page_size + 1)).all()
        
        has_next = len(items) > page_size
        if has_next:
            items = items[:-1]
        
        next_cursor = getattr(items[-1], order_column.name) if items and has_next else None
        
        return {
            "items": items,
            "has_next": has_next,
            "next_cursor": next_cursor
        }
    
    def efficient_counting(self, model_class, filters=None) -> int:
        """高效计数查询"""
        # 对于大表，使用近似计数
        try:
            # PostgreSQL的近似计数
            if filters is None:
                result = self.session.execute(
                    text(f"""
                    SELECT reltuples::bigint AS estimate
                    FROM pg_class
                    WHERE relname = '{model_class.__tablename__}'
                    """)
                ).scalar()
                
                if result and result > 1000000:  # 大于100万行使用估算
                    return result
        except Exception:
            pass
        
        # 精确计数
        query = select(func.count()).select_from(model_class)
        if filters:
            query = query.where(filters)
        
        return self.session.exec(query).one()
    
    def batch_processing(self, model_class, batch_size: int = 1000, 
                        filters=None, process_func=None):
        """批量处理大数据集"""
        offset = 0
        
        while True:
            query = select(model_class)
            if filters:
                query = query.where(filters)
            
            batch = self.session.exec(
                query.offset(offset).limit(batch_size)
            ).all()
            
            if not batch:
                break
            
            # 处理批次
            if process_func:
                process_func(batch)
            
            offset += batch_size
            
            # 清理会话缓存
            self.session.expunge_all()
    
    def optimized_joins(self, base_model, join_models: List, 
                       select_columns=None) -> List:
        """优化的JOIN查询"""
        # 构建查询
        if select_columns:
            query = select(*select_columns)
        else:
            query = select(base_model)
        
        # 添加JOIN
        for join_model, join_condition in join_models:
            query = query.join(join_model, join_condition)
        
        return self.session.exec(query).all()
    
    def conditional_loading(self, model_class, load_relationships: bool = False,
                          relationship_names: List[str] = None):
        """条件性加载关联数据"""
        query = select(model_class)
        
        if load_relationships and relationship_names:
            from sqlalchemy.orm import selectinload
            
            options = []
            for rel_name in relationship_names:
                options.append(selectinload(getattr(model_class, rel_name)))
            
            query = query.options(*options)
        
        return self.session.exec(query).all()
    
    def query_result_caching(self, query_key: str, query_func, 
                           cache_duration: int = 300):
        """查询结果缓存"""
        # 简单的内存缓存实现
        if not hasattr(self, '_cache'):
            self._cache = {}
        
        now = datetime.utcnow()
        
        # 检查缓存
        if query_key in self._cache:
            cached_data, cached_time = self._cache[query_key]
            if (now - cached_time).seconds < cache_duration:
                return cached_data
        
        # 执行查询
        result = query_func()
        
        # 缓存结果
        self._cache[query_key] = (result, now)
        
        return result
    
    def explain_query_performance(self, query) -> Dict[str, Any]:
        """分析查询性能"""
        # 获取查询执行计划
        explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
        
        try:
            result = self.session.execute(text(explain_query)).fetchone()
            plan_data = result[0][0]  # JSON格式的执行计划
            
            return {
                "execution_time": plan_data.get("Execution Time", 0),
                "planning_time": plan_data.get("Planning Time", 0),
                "total_cost": plan_data.get("Plan", {}).get("Total Cost", 0),
                "rows_returned": plan_data.get("Plan", {}).get("Actual Rows", 0),
                "plan_details": plan_data
            }
        except Exception as e:
            return {"error": str(e)}

# 使用示例
def demonstrate_query_best_practices():
    """演示查询最佳实践"""
    engine = create_engine("postgresql://user:pass@localhost/db")
    
    with Session(engine) as session:
        practices = QueryBestPractices(session)
        
        # 高效分页
        page_result = practices.efficient_pagination(
            User, page=1, page_size=20, order_column=User.created_at
        )
        print(f"分页结果: {len(page_result['items'])} 项，共 {page_result['total']} 项")
        
        # 批量处理
        def process_batch(users):
            print(f"处理 {len(users)} 个用户")
        
        practices.batch_processing(
            User, 
            batch_size=1000, 
            process_func=process_batch
        )
        
        # 条件性加载
        users_with_orders = practices.conditional_loading(
            User, 
            load_relationships=True, 
            relationship_names=['orders']
        )
        print(f"加载了 {len(users_with_orders)} 个用户及其订单")
        
        # 查询缓存
        def expensive_query():
            return session.exec(
                select(func.count(User.id))
            ).one()
        
        count = practices.query_result_caching(
             "user_count", 
             expensive_query, 
             cache_duration=600
         )
         print(f"用户总数: {count}")
```

### 8.2 性能监控最佳实践

```python
# monitoring_best_practices.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import event, create_engine, text
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import time
import logging
import json

class PerformanceMonitoringBestPractices:
    """性能监控最佳实践"""
    
    def __init__(self, engine):
        self.engine = engine
        self.query_stats = []
        self.slow_query_threshold = 1.0  # 1秒
        self.setup_monitoring()
    
    def setup_monitoring(self):
        """设置性能监控"""
        # 监听查询执行
        @event.listens_for(self.engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(self.engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total_time = time.time() - context._query_start_time
            
            # 记录查询统计
            query_stat = {
                "query": statement[:200],  # 截取前200字符
                "execution_time": total_time,
                "timestamp": datetime.utcnow(),
                "parameters": str(parameters)[:100] if parameters else None
            }
            
            self.query_stats.append(query_stat)
            
            # 记录慢查询
            if total_time > self.slow_query_threshold:
                logging.warning(
                    f"慢查询检测: {total_time:.3f}s - {statement[:100]}..."
                )
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """获取性能摘要"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_queries = [
            stat for stat in self.query_stats 
            if stat['timestamp'] > cutoff_time
        ]
        
        if not recent_queries:
            return {"message": "没有查询数据"}
        
        execution_times = [q['execution_time'] for q in recent_queries]
        slow_queries = [q for q in recent_queries if q['execution_time'] > self.slow_query_threshold]
        
        return {
            "时间范围": f"最近 {hours} 小时",
            "总查询数": len(recent_queries),
            "慢查询数": len(slow_queries),
            "平均执行时间": sum(execution_times) / len(execution_times),
            "最大执行时间": max(execution_times),
            "最小执行时间": min(execution_times),
            "慢查询比例": f"{len(slow_queries) / len(recent_queries) * 100:.2f}%",
            "最慢的5个查询": sorted(
                recent_queries, 
                key=lambda x: x['execution_time'], 
                reverse=True
            )[:5]
        }
    
    def setup_alerting(self, alert_threshold: float = 2.0, 
                      alert_callback=None):
        """设置告警"""
        @event.listens_for(self.engine, "after_cursor_execute")
        def check_for_alerts(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, '_query_start_time'):
                total_time = time.time() - context._query_start_time
                
                if total_time > alert_threshold:
                    alert_data = {
                        "type": "slow_query",
                        "execution_time": total_time,
                        "query": statement[:200],
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    if alert_callback:
                        alert_callback(alert_data)
                    else:
                        logging.critical(f"严重慢查询告警: {total_time:.3f}s")
    
    def generate_performance_report(self) -> str:
        """生成性能报告"""
        summary = self.get_performance_summary(24)  # 24小时数据
        
        report = f"""
# SQLModel 性能报告

## 概览
- 报告时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
- 统计时间范围: {summary.get('时间范围', 'N/A')}
- 总查询数: {summary.get('总查询数', 0)}
- 慢查询数: {summary.get('慢查询数', 0)}
- 慢查询比例: {summary.get('慢查询比例', '0%')}

## 性能指标
- 平均执行时间: {summary.get('平均执行时间', 0):.3f}s
- 最大执行时间: {summary.get('最大执行时间', 0):.3f}s
- 最小执行时间: {summary.get('最小执行时间', 0):.3f}s

## 最慢查询 Top 5
"""
        
        slow_queries = summary.get('最慢的5个查询', [])
        for i, query in enumerate(slow_queries, 1):
            report += f"""
### {i}. 执行时间: {query['execution_time']:.3f}s
```sql
{query['query']}
```
"""
        
        return report
    
    def optimize_connection_pool(self) -> Dict[str, Any]:
        """连接池优化建议"""
        # 分析连接使用模式
        recent_queries = self.query_stats[-1000:]  # 最近1000个查询
        
        if not recent_queries:
            return {"message": "没有足够的查询数据"}
        
        # 计算查询频率
        time_diffs = []
        for i in range(1, len(recent_queries)):
            diff = (recent_queries[i]['timestamp'] - recent_queries[i-1]['timestamp']).total_seconds()
            time_diffs.append(diff)
        
        avg_interval = sum(time_diffs) / len(time_diffs) if time_diffs else 0
        
        recommendations = {
            "当前查询间隔": f"{avg_interval:.3f}s",
            "建议连接池大小": max(5, min(20, int(1 / avg_interval) if avg_interval > 0 else 10)),
            "建议最大溢出": 10,
            "建议连接超时": 30,
            "建议连接回收时间": 3600
        }
        
        if avg_interval < 0.1:
            recommendations["特别建议"] = "查询频率很高，考虑增加连接池大小和使用连接复用"
        elif avg_interval > 10:
            recommendations["特别建议"] = "查询频率较低，可以减少连接池大小以节省资源"
        
        return recommendations
    
    def cleanup_old_stats(self, days: int = 7):
        """清理旧的统计数据"""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        self.query_stats = [
            stat for stat in self.query_stats 
            if stat['timestamp'] > cutoff_time
        ]
        
        logging.info(f"清理了 {days} 天前的统计数据")

# 使用示例
def setup_comprehensive_monitoring():
    """设置全面的性能监控"""
    engine = create_engine(
        "postgresql://user:pass@localhost/db",
        echo=False,  # 关闭SQLAlchemy的查询日志，使用自定义监控
        pool_size=10,
        max_overflow=20
    )
    
    # 设置监控
    monitor = PerformanceMonitoringBestPractices(engine)
    
    # 设置告警回调
    def alert_callback(alert_data):
        # 这里可以集成邮件、Slack、钉钉等告警系统
        print(f"🚨 性能告警: {alert_data}")
        
        # 可以发送到监控系统
        # send_to_monitoring_system(alert_data)
    
    monitor.setup_alerting(alert_threshold=2.0, alert_callback=alert_callback)
    
    return monitor, engine

# 定期报告生成
def generate_daily_report(monitor: PerformanceMonitoringBestPractices):
    """生成每日性能报告"""
    report = monitor.generate_performance_report()
    
    # 保存报告
    filename = f"performance_report_{datetime.utcnow().strftime('%Y%m%d')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"性能报告已保存到: {filename}")
    
    # 清理旧数据
    monitor.cleanup_old_stats(days=7)
    
    return report
```

### 8.3 团队协作最佳实践

```python
# team_collaboration.py
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy import create_engine, text
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os

class TeamCollaborationBestPractices:
    """团队协作最佳实践"""
    
    @staticmethod
    def create_performance_standards() -> Dict[str, Any]:
        """创建性能标准"""
        return {
            "查询性能标准": {
                "简单查询": "< 100ms",
                "复杂查询": "< 500ms",
                "报表查询": "< 2s",
                "批量操作": "< 10s"
            },
            "索引标准": {
                "主键索引": "必须",
                "外键索引": "必须",
                "查询字段索引": "根据使用频率",
                "复合索引": "优先考虑查询模式"
            },
            "代码审查检查点": [
                "是否使用了适当的索引",
                "是否避免了N+1查询",
                "是否使用了合适的预加载策略",
                "是否有适当的错误处理",
                "是否遵循了命名约定",
                "是否添加了必要的注释"
            ],
            "性能测试要求": {
                "单元测试": "每个查询方法",
                "集成测试": "完整的业务流程",
                "负载测试": "预期并发用户数的2倍",
                "压力测试": "系统极限测试"
            }
        }
    
    @staticmethod
    def create_development_guidelines() -> str:
        """创建开发指南"""
        return """
# SQLModel 开发指南

## 1. 模型设计原则

### 1.1 命名约定
- 模型类名使用 PascalCase
- 字段名使用 snake_case
- 表名使用复数形式
- 索引名使用 `idx_` 前缀

### 1.2 字段定义
```python
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
```

## 2. 查询最佳实践

### 2.1 避免 N+1 查询
```python
# ❌ 错误方式
users = session.exec(select(User)).all()
for user in users:
    orders = session.exec(select(Order).where(Order.user_id == user.id)).all()

# ✅ 正确方式
from sqlalchemy.orm import selectinload
users = session.exec(
    select(User).options(selectinload(User.orders))
).all()
```

### 2.2 使用适当的索引
```python
# 为经常查询的字段创建索引
class Order(SQLModel, table=True):
    status: str = Field(index=True)  # 经常用于过滤
    created_at: datetime = Field(index=True)  # 经常用于排序
```

### 2.3 分页查询
```python
# 使用 LIMIT 和 OFFSET
def get_users_page(session: Session, page: int, page_size: int):
    offset = (page - 1) * page_size
    return session.exec(
        select(User)
        .order_by(User.id)
        .offset(offset)
        .limit(page_size)
    ).all()
```

## 3. 错误处理

### 3.1 数据库异常处理
```python
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

try:
    session.add(user)
    session.commit()
except IntegrityError as e:
    session.rollback()
    raise ValueError(f"数据完整性错误: {e}")
except SQLAlchemyError as e:
    session.rollback()
    raise RuntimeError(f"数据库错误: {e}")
```

## 4. 测试指南

### 4.1 单元测试
```python
def test_user_creation():
    with Session(test_engine) as session:
        user = User(email="test@example.com")
        session.add(user)
        session.commit()
        
        assert user.id is not None
        assert user.email == "test@example.com"
```

### 4.2 性能测试
```python
import time

def test_query_performance():
    start_time = time.time()
    
    with Session(engine) as session:
        users = session.exec(select(User).limit(1000)).all()
    
    execution_time = time.time() - start_time
    assert execution_time < 1.0, f"查询太慢: {execution_time}s"
```

## 5. 代码审查清单

- [ ] 模型定义是否完整和正确
- [ ] 是否使用了适当的字段类型和约束
- [ ] 是否创建了必要的索引
- [ ] 查询是否高效（避免N+1问题）
- [ ] 是否有适当的错误处理
- [ ] 是否有单元测试覆盖
- [ ] 是否遵循命名约定
- [ ] 是否有适当的文档注释
"""
    
    @staticmethod
    def create_performance_checklist() -> List[str]:
        """创建性能检查清单"""
        return [
            "✅ 数据库连接配置优化",
            "✅ 索引策略制定和实施",
            "✅ 查询优化（避免N+1查询）",
            "✅ 适当的预加载策略",
            "✅ 分页查询实现",
            "✅ 批量操作优化",
            "✅ 缓存策略实施",
            "✅ 性能监控设置",
            "✅ 慢查询日志配置",
            "✅ 错误处理和日志记录",
            "✅ 单元测试和集成测试",
            "✅ 性能基准测试",
            "✅ 代码审查流程",
            "✅ 文档和注释完整性",
            "✅ 生产环境监控"
        ]
    
    @staticmethod
    def setup_project_structure() -> Dict[str, str]:
        """设置项目结构"""
        return {
            "models/": "数据模型定义",
            "models/__init__.py": "模型导入",
            "models/user.py": "用户模型",
            "models/order.py": "订单模型",
            "services/": "业务逻辑服务",
            "services/user_service.py": "用户服务",
            "services/order_service.py": "订单服务",
            "repositories/": "数据访问层",
            "repositories/base.py": "基础仓储",
            "repositories/user_repository.py": "用户仓储",
            "database/": "数据库配置",
            "database/connection.py": "数据库连接",
            "database/migrations/": "数据库迁移",
            "tests/": "测试文件",
            "tests/test_models.py": "模型测试",
            "tests/test_services.py": "服务测试",
            "tests/performance/": "性能测试",
            "docs/": "项目文档",
            "docs/api.md": "API文档",
            "docs/performance.md": "性能指南"
        }

# 使用示例
def setup_team_standards():
    """设置团队标准"""
    collaboration = TeamCollaborationBestPractices()
    
    # 创建性能标准文档
    standards = collaboration.create_performance_standards()
    with open("performance_standards.json", "w", encoding="utf-8") as f:
        json.dump(standards, f, indent=2, ensure_ascii=False)
    
    # 创建开发指南
    guidelines = collaboration.create_development_guidelines()
    with open("development_guidelines.md", "w", encoding="utf-8") as f:
        f.write(guidelines)
    
    # 创建检查清单
    checklist = collaboration.create_performance_checklist()
    with open("performance_checklist.md", "w", encoding="utf-8") as f:
        f.write("# 性能优化检查清单\n\n")
        for item in checklist:
            f.write(f"- {item}\n")
    
    # 创建项目结构说明
    structure = collaboration.setup_project_structure()
    with open("project_structure.md", "w", encoding="utf-8") as f:
        f.write("# 项目结构说明\n\n")
        for path, description in structure.items():
            f.write(f"- `{path}`: {description}\n")
    
    print("团队协作标准文档已创建完成！")
```

---

## 9. 本章总结

### 9.1 核心概念回顾

本章深入探讨了 SQLModel 查询优化与性能调优的各个方面：

**查询执行原理**
- 查询解析和优化过程
- 执行计划分析
- 成本估算机制

**基础查询优化**
- SELECT 语句优化
- WHERE 条件优化
- JOIN 查询优化
- 排序和分组优化

**索引策略**
- 索引类型选择
- 复合索引设计
- 索引监控和维护

**高级优化技术**
- 查询计划分析
- 并行查询处理
- 异步查询优化

**缓存策略**
- 查询结果缓存
- 应用级缓存
- 多级缓存架构

**性能监控**
- 实时性能监控
- 系统资源监控
- 告警机制

### 9.2 最佳实践总结

**查询优化最佳实践**
1. **避免 N+1 查询问题**
   - 使用预加载（selectinload、joinedload）
   - 批量查询关联数据
   - 合理使用 JOIN 查询

2. **高效分页实现**
   - 小偏移量使用 OFFSET/LIMIT
   - 大偏移量使用游标分页
   - 缓存总数统计

3. **索引优化策略**
   - 为查询字段创建索引
   - 优化复合索引列顺序
   - 使用部分索引和函数索引
   - 定期监控索引使用情况

4. **批量操作优化**
   - 使用 bulk 操作
   - 分批处理大数据集
   - 适当的事务边界

**性能监控最佳实践**
1. **建立监控体系**
   - 查询性能监控
   - 系统资源监控
   - 业务指标监控

2. **设置告警机制**
   - 慢查询告警
   - 资源使用告警
   - 错误率告警

3. **定期性能审查**
   - 生成性能报告
   - 分析性能趋势
   - 优化建议实施

**团队协作最佳实践**
1. **制定开发标准**
   - 代码规范
   - 性能标准
   - 审查流程

2. **建立测试体系**
   - 单元测试
   - 性能测试
   - 集成测试

3. **文档和知识分享**
   - 技术文档
   - 最佳实践分享
   - 问题解决方案库

### 9.3 常见陷阱与避免方法

**查询性能陷阱**
1. **N+1 查询问题**
   - 陷阱：在循环中执行查询
   - 避免：使用预加载或批量查询

2. **过度预加载**
   - 陷阱：加载不需要的关联数据
   - 避免：按需加载，选择性预加载

3. **缺失索引**
   - 陷阱：查询字段没有索引
   - 避免：分析查询模式，创建合适索引

4. **不当的分页**
   - 陷阱：大偏移量分页性能差
   - 避免：使用游标分页或优化查询

**索引设计陷阱**
1. **索引过多**
   - 陷阱：为每个字段都创建索引
   - 避免：根据查询模式创建必要索引

2. **复合索引列顺序错误**
   - 陷阱：选择性低的列在前
   - 避免：将选择性高的列放在前面

3. **忽略索引维护**
   - 陷阱：索引统计信息过时
   - 避免：定期更新统计信息

**缓存策略陷阱**
1. **缓存雪崩**
   - 陷阱：大量缓存同时失效
   - 避免：设置随机过期时间

2. **缓存穿透**
   - 陷阱：查询不存在的数据
   - 避免：缓存空结果或使用布隆过滤器

3. **缓存一致性问题**
   - 陷阱：数据更新后缓存未失效
   - 避免：实施缓存失效策略

### 9.4 实践检查清单

**开发阶段**
- [ ] 模型设计是否合理
- [ ] 字段类型和约束是否正确
- [ ] 索引策略是否制定
- [ ] 查询是否优化
- [ ] 错误处理是否完善
- [ ] 单元测试是否覆盖

**测试阶段**
- [ ] 性能测试是否通过
- [ ] 负载测试是否满足要求
- [ ] 内存使用是否合理
- [ ] 并发处理是否正常
- [ ] 错误场景是否处理

**部署阶段**
- [ ] 数据库配置是否优化
- [ ] 连接池配置是否合理
- [ ] 监控系统是否部署
- [ ] 告警规则是否设置
- [ ] 备份策略是否制定

**运维阶段**
- [ ] 性能指标是否正常
- [ ] 慢查询是否及时处理
- [ ] 索引是否需要调整
- [ ] 缓存命中率是否合理
- [ ] 系统资源使用是否正常

### 9.5 下一步学习

**深入学习方向**
1. **数据库内核优化**
   - 查询优化器原理
   - 存储引擎优化
   - 分布式数据库

2. **高级缓存技术**
   - Redis 集群
   - 分布式缓存
   - 缓存一致性协议

3. **微服务架构下的数据访问**
   - 数据库分片
   - 读写分离
   - 事务一致性

4. **云原生数据库**
   - 容器化部署
   - 自动扩缩容
   - 多云数据库管理

**实践项目建议**
1. **性能监控系统**
   - 构建完整的监控体系
   - 实现自动化告警
   - 开发性能分析工具

2. **查询优化工具**
   - 开发查询分析器
   - 实现自动索引建议
   - 构建性能基准测试

3. **缓存管理系统**
   - 实现多级缓存
   - 开发缓存管理界面
   - 构建缓存性能分析

### 9.6 扩展练习

**基础练习**
1. 实现一个完整的用户管理系统，包含性能优化
2. 设计并实现高效的分页查询方案
3. 创建索引监控和优化工具

**进阶练习**
1. 构建多级缓存系统
2. 实现查询性能自动分析工具
3. 开发数据库性能监控仪表板

**高级练习**
1. 设计分布式数据访问层
2. 实现自适应查询优化系统
3. 构建智能数据库运维平台

通过本章的学习，你应该能够：
- 理解查询执行原理和优化策略
- 掌握索引设计和维护技巧
- 实施有效的缓存策略
- 建立完善的性能监控体系
- 解决常见的性能问题
- 在团队中推广最佳实践

继续下一章的学习，我们将探讨 SQLModel 在生产环境中的部署和运维最佳实践。
```