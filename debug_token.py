#!/usr/bin/env python3
"""
Token 诊断工具 - 检查 JWT Token 问题
"""

import sys
from datetime import datetime
from jose import jwt, JWTError
from app.core.config import settings

def diagnose_token(token: str):
    """诊断 JWT Token"""

    print("=" * 60)
    print("JWT Token 诊断工具")
    print("=" * 60)

    # 1. 检查 token 格式
    print("\n[1] Token 格式检查:")
    parts = token.split('.')
    if len(parts) != 3:
        print(f"   ❌ 错误: Token 格式无效 (应该有3部分，实际有{len(parts)}部分)")
        return
    else:
        print(f"   ✅ Token 格式正确 (3部分)")
        print(f"   Header长度: {len(parts[0])} 字符")
        print(f"   Payload长度: {len(parts[1])} 字符")
        print(f"   Signature长度: {len(parts[2])} 字符")

    # 2. 尝试解码 token (不验证签名)
    print("\n[2] Token 内容解码 (不验证签名):")
    try:
        unverified_payload = jwt.get_unverified_claims(token)
        print("   ✅ Token 可以解码")
        print(f"   Payload内容:")
        for key, value in unverified_payload.items():
            if key == 'exp':
                exp_time = datetime.fromtimestamp(value)
                now = datetime.utcnow()
                if exp_time > now:
                    print(f"   - {key}: {value} ({exp_time}) ✅ 未过期")
                else:
                    print(f"   - {key}: {value} ({exp_time}) ❌ 已过期 (当前时间: {now})")
            else:
                print(f"   - {key}: {value}")
    except Exception as e:
        print(f"   ❌ 无法解码 Token: {e}")
        return

    # 3. 检查配置
    print("\n[3] 配置检查:")
    print(f"   SECRET_KEY: {settings.SECRET_KEY[:20]}... ({len(settings.SECRET_KEY)} 字符)")
    print(f"   JWT_ALGORITHM: {settings.JWT_ALGORITHM}")
    print(f"   ACCESS_TOKEN_EXPIRE: {settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES} 分钟")

    # 4. 验证签名
    print("\n[4] Token 签名验证:")
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        print("   ✅ 签名验证成功")
    except jwt.ExpiredSignatureError:
        print("   ❌ Token 已过期")
        exp_time = datetime.fromtimestamp(unverified_payload.get('exp', 0))
        now = datetime.utcnow()
        expired_delta = now - exp_time
        print(f"   过期时间: {exp_time}")
        print(f"   当前时间: {now}")
        print(f"   过期了: {expired_delta}")
        return
    except jwt.JWTClaimsError as e:
        print(f"   ❌ Token claims 错误: {e}")
        return
    except jwt.JWTError as e:
        print(f"   ❌ 签名验证失败: {e}")
        print(f"   可能原因:")
        print(f"   - SECRET_KEY 不匹配")
        print(f"   - Token 被篡改")
        print(f"   - Token 使用了不同的算法")
        return

    # 5. 检查 token 类型
    print("\n[5] Token 类型检查:")
    token_type = payload.get("type")
    if token_type == "access":
        print("   ✅ 正确的 access token")
    elif token_type == "refresh":
        print("   ❌ 这是 refresh token，不能用于 API 认证")
        print("   请使用 access token 或刷新获取新的 access token")
    else:
        print(f"   ⚠️  未知的 token 类型: {token_type}")

    # 6. 检查必需字段
    print("\n[6] 必需字段检查:")
    required_fields = ["sub", "exp", "type"]
    all_present = True
    for field in required_fields:
        if field in payload:
            print(f"   ✅ {field}: {payload[field]}")
        else:
            print(f"   ❌ 缺少必需字段: {field}")
            all_present = False

    if not all_present:
        print("\n   Token 缺少必需字段")
        return

    # 7. 检查用户是否存在
    print("\n[7] 用户检查:")
    user_id = payload.get("sub")
    print(f"   用户 ID: {user_id}")

    import asyncio
    from app.db.base import get_db_read
    from app.models.user import User
    from sqlalchemy import select

    async def check_user():
        async for db in get_db_read():
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                print(f"   ✅ 用户存在")
                print(f"   - Email: {user.email}")
                print(f"   - Username: {user.username}")
                print(f"   - Active: {user.is_active}")
                print(f"   - Deleted: {user.is_deleted}")

                if user.is_deleted:
                    print(f"   ❌ 用户已被删除")
                elif not user.is_active:
                    print(f"   ❌ 用户未激活")
                else:
                    print(f"   ✅ 用户状态正常")
            else:
                print(f"   ❌ 用户不存在")
            break

    try:
        asyncio.run(check_user())
    except Exception as e:
        print(f"   ❌ 检查用户时出错: {e}")

    # 总结
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("用法: python debug_token.py <JWT_TOKEN>")
        print("\n示例:")
        print("  python debug_token.py eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        sys.exit(1)

    token = sys.argv[1]
    diagnose_token(token)


if __name__ == "__main__":
    main()
