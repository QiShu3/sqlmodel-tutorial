from typing import List
from sqlmodel import Session, select
from config.database import create_db_and_tables, get_session
from models.hero import Hero, HeroCreate

def create_hero(session: Session, hero_data: HeroCreate) -> Hero:
    """创建英雄"""
    hero = Hero.from_orm(hero_data)
    session.add(hero)
    session.commit()
    session.refresh(hero)
    print(f"✅ 创建英雄成功: {hero.name}")
    return hero

def get_heroes(session: Session) -> List[Hero]:
    """获取所有英雄"""
    statement = select(Hero)
    heroes = session.exec(statement).all()
    print(f"📋 找到 {len(heroes)} 个英雄")
    return heroes

def get_hero_by_id(session: Session, hero_id: int) -> Hero | None:
    """根据 ID 获取英雄"""
    hero = session.get(Hero, hero_id)
    if hero:
        print(f"🔍 找到英雄: {hero.name}")
    else:
        print(f"❌ 未找到 ID 为 {hero_id} 的英雄")
    return hero

def update_hero(session: Session, hero_id: int, hero_data: dict) -> Hero | None:
    """更新英雄信息"""
    hero = session.get(Hero, hero_id)
    if not hero:
        print(f"❌ 未找到 ID 为 {hero_id} 的英雄")
        return None
    
    for key, value in hero_data.items():
        if hasattr(hero, key) and value is not None:
            setattr(hero, key, value)
    
    session.add(hero)
    session.commit()
    session.refresh(hero)
    print(f"✅ 更新英雄成功: {hero.name}")
    return hero

def delete_hero(session: Session, hero_id: int) -> bool:
    """删除英雄"""
    hero = session.get(Hero, hero_id)
    if not hero:
        print(f"❌ 未找到 ID 为 {hero_id} 的英雄")
        return False
    
    session.delete(hero)
    session.commit()
    print(f"🗑️ 删除英雄成功: {hero.name}")
    return True

def main():
    """主函数 - 演示 CRUD 操作"""
    print("🚀 SQLModel 教程 - 第一个程序")
    print("=" * 40)
    
    # 创建数据库表
    create_db_and_tables()
    
    # 获取数据库会话
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        # 1. 创建英雄
        print("\n1️⃣ 创建英雄")
        hero1_data = HeroCreate(
            name="Spider-Man",
            secret_name="Peter Parker",
            age=25
        )
        hero1 = create_hero(session, hero1_data)
        
        hero2_data = HeroCreate(
            name="Iron Man",
            secret_name="Tony Stark",
            age=45
        )
        hero2 = create_hero(session, hero2_data)
        
        # 2. 查询所有英雄
        print("\n2️⃣ 查询所有英雄")
        all_heroes = get_heroes(session)
        for hero in all_heroes:
            print(f"  - {hero.name} ({hero.secret_name}), 年龄: {hero.age}")
        
        # 3. 根据 ID 查询英雄
        print("\n3️⃣ 根据 ID 查询英雄")
        hero = get_hero_by_id(session, 1)
        if hero:
            print(f"  英雄详情: {hero.name}, 创建时间: {hero.created_at}")
        
        # 4. 更新英雄信息
        print("\n4️⃣ 更新英雄信息")
        updated_hero = update_hero(session, 1, {"age": 26})
        if updated_hero:
            print(f"  更新后年龄: {updated_hero.age}")
        
        # 5. 删除英雄
        print("\n5️⃣ 删除英雄")
        delete_success = delete_hero(session, 2)
        
        # 6. 再次查询验证
        print("\n6️⃣ 验证删除结果")
        remaining_heroes = get_heroes(session)
        for hero in remaining_heroes:
            print(f"  - {hero.name} ({hero.secret_name})")
            
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        session.rollback()
    finally:
        session.close()
        print("\n🎉 程序执行完成")

if __name__ == "__main__":
    main()