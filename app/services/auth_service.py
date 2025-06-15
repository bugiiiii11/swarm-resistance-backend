# app/services/auth_service.py
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import httpx
import uuid
import hashlib
import secrets
import logging
import re

from app.config import settings
from app.database import execute_query, execute_command
from app.models.user import User, UserCreate, UserUpdate, TokenVerificationResult

# Set up logging
logger = logging.getLogger(__name__)

class AuthService:
    """Authentication service for Web3Auth integration and JWT management"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.token_expire_minutes = settings.access_token_expire_minutes
        self.max_login_attempts = settings.max_login_attempts
        self.lockout_duration = settings.lockout_duration_minutes
        
        logger.info("✅ Authentication service initialized")

    async def verify_web3auth_token(self, token: str) -> TokenVerificationResult:
        """Verify Web3Auth JWT token and extract user information"""
        try:
            # Decode the Web3Auth token (without signature verification for now)
            # In production, you should verify the token with Web3Auth's public key
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            # Extract user information from Web3Auth token
            user_id = decoded.get("sub") or decoded.get("user_id")
            email = decoded.get("email")
            name = decoded.get("name") or decoded.get("nickname")
            
            # Extract wallet address from different possible locations
            wallet_address = None
            
            # Try different ways Web3Auth might structure the wallet data
            if "wallets" in decoded and decoded["wallets"]:
                # Standard Web3Auth format
                wallet_address = decoded["wallets"][0].get("public_key")
            elif "publicKey" in decoded:
                # Alternative format
                wallet_address = decoded["publicKey"]
            elif "address" in decoded:
                # Direct address
                wallet_address = decoded["address"]
            elif "wallet_address" in decoded:
                # Custom field
                wallet_address = decoded["wallet_address"]
            
            if not wallet_address:
                raise ValueError("No wallet address found in Web3Auth token")
            
            # Validate and normalize wallet address
            wallet_address = self._validate_wallet_address(wallet_address)
            
            # Extract provider information
            provider = decoded.get("iss") or decoded.get("provider") or "web3auth"
            
            result = TokenVerificationResult(
                user_id=user_id or str(uuid.uuid4()),
                wallet_address=wallet_address,
                email=email,
                name=name,
                provider=provider,
                verified=True
            )
            
            logger.info(f"✅ Web3Auth token verified for wallet: {wallet_address}")
            return result
            
        except jwt.ExpiredSignatureError:
            logger.error("Web3Auth token has expired")
            raise Exception("Web3Auth token has expired")
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid Web3Auth token: {str(e)}")
            raise Exception(f"Invalid Web3Auth token: {str(e)}")
        except Exception as e:
            logger.error(f"Web3Auth token verification failed: {str(e)}")
            raise Exception(f"Web3Auth token verification failed: {str(e)}")

    def _validate_wallet_address(self, address: str) -> str:
        """Validate and normalize Ethereum wallet address"""
        if not address:
            raise ValueError("Wallet address is required")
        
        # Remove whitespace and convert to lowercase
        address = address.strip().lower()
        
        # Check if it's a valid Ethereum address format
        if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            raise ValueError("Invalid wallet address format")
        
        return address

    async def get_or_create_user(self, user_data: TokenVerificationResult, db=None) -> User:
        """Get existing user or create new one"""
        wallet_address = user_data.wallet_address.lower()
        
        try:
            # Check if user exists
            existing_user = await execute_query(
                "SELECT * FROM users WHERE wallet_address = $1",
                wallet_address
            )
            
            if existing_user:
                user_record = existing_user[0]
                
                # Update last login time
                await execute_command(
                    "UPDATE users SET last_login = $1 WHERE id = $2",
                    datetime.utcnow(),
                    user_record["id"]
                )
                
                logger.info(f"✅ Existing user login: {wallet_address}")
                
                return User(
                    id=user_record["id"],
                    wallet_address=user_record["wallet_address"],
                    email=user_record["email"],
                    username=user_record["username"],
                    web3auth_user_id=user_record["web3auth_user_id"],
                    is_admin=user_record["is_admin"],
                    is_active=user_record["is_active"],
                    last_login=datetime.utcnow(),
                    created_at=user_record["created_at"],
                    updated_at=user_record["updated_at"]
                )
            
            # Create new user
            user_id = str(uuid.uuid4())
            username = self._generate_username_from_wallet(wallet_address)
            
            await execute_command(
                """INSERT INTO users 
                   (id, wallet_address, email, username, web3auth_user_id, last_login)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                user_id,
                wallet_address,
                user_data.email,
                username,
                user_data.user_id,
                datetime.utcnow()
            )
            
            # Log user creation activity
            await self._log_user_activity(
                user_id,
                "user_created",
                {
                    "wallet_address": wallet_address,
                    "provider": user_data.provider,
                    "has_email": bool(user_data.email)
                }
            )
            
            logger.info(f"✅ New user created: {wallet_address}")
            
            # Return the created user
            new_user = await execute_query(
                "SELECT * FROM users WHERE id = $1",
                user_id
            )
            
            user_record = new_user[0]
            return User(
                id=user_record["id"],
                wallet_address=user_record["wallet_address"],
                email=user_record["email"],
                username=user_record["username"],
                web3auth_user_id=user_record["web3auth_user_id"],
                is_admin=user_record["is_admin"],
                is_active=user_record["is_active"],
                last_login=user_record["last_login"],
                created_at=user_record["created_at"],
                updated_at=user_record["updated_at"]
            )
            
        except Exception as e:
            logger.error(f"Failed to get or create user: {str(e)}")
            raise Exception(f"User authentication failed: {str(e)}")

    def _generate_username_from_wallet(self, wallet_address: str) -> str:
        """Generate a unique username from wallet address"""
        # Take first 6 and last 4 characters of wallet address
        short_address = f"{wallet_address[:6]}{wallet_address[-4:]}"
        # Add some randomness to ensure uniqueness
        random_suffix = secrets.token_hex(2)
        return f"user_{short_address}_{random_suffix}"

    def create_access_token(self, user_id: str, additional_claims: Dict[str, Any] = None) -> str:
        """Create JWT access token for user"""
        expire = datetime.utcnow() + timedelta(minutes=self.token_expire_minutes)
        
        # Base token claims
        to_encode = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access_token",
            "iss": settings.app_name
        }
        
        # Add any additional claims
        if additional_claims:
            to_encode.update(additional_claims)
        
        token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"✅ Access token created for user: {user_id}")
        return token

    async def verify_token(self, token: str) -> User:
        """Verify JWT token and return user"""
        try:
            # Decode and verify the token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("sub")
            
            if user_id is None:
                raise Exception("Invalid token: missing user ID")
            
            # Check token type
            if payload.get("type") != "access_token":
                raise Exception("Invalid token type")
            
            # Get user from database
            user_data = await execute_query(
                "SELECT * FROM users WHERE id = $1 AND is_active = TRUE",
                user_id
            )
            
            if not user_data:
                raise Exception("User not found or inactive")
            
            user_record = user_data[0]
            
            return User(
                id=user_record["id"],
                wallet_address=user_record["wallet_address"],
                email=user_record["email"],
                username=user_record["username"],
                web3auth_user_id=user_record["web3auth_user_id"],
                is_admin=user_record["is_admin"],
                is_active=user_record["is_active"],
                last_login=user_record["last_login"],
                created_at=user_record["created_at"],
                updated_at=user_record["updated_at"]
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise Exception("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            raise Exception("Invalid token")
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise Exception(f"Token verification failed: {str(e)}")

    async def refresh_token(self, refresh_token: str) -> str:
        """Refresh an access token using refresh token"""
        try:
            # Decode refresh token
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algorithm])
            
            if payload.get("type") != "refresh_token":
                raise Exception("Invalid refresh token")
            
            user_id = payload.get("sub")
            if not user_id:
                raise Exception("Invalid refresh token: missing user ID")
            
            # Verify user still exists and is active
            user_exists = await execute_query(
                "SELECT id FROM users WHERE id = $1 AND is_active = TRUE",
                user_id
            )
            
            if not user_exists:
                raise Exception("User not found or inactive")
            
            # Create new access token
            new_token = self.create_access_token(user_id)
            
            logger.info(f"✅ Token refreshed for user: {user_id}")
            return new_token
            
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            raise Exception(f"Token refresh failed: {str(e)}")

    async def update_user(self, user_id: str, user_update: UserUpdate, db=None) -> User:
        """Update user profile"""
        try:
            update_data = user_update.dict(exclude_unset=True)
            
            if not update_data:
                # No updates provided, return current user
                user_data = await execute_query("SELECT * FROM users WHERE id = $1", user_id)
                if not user_data:
                    raise Exception("User not found")
                
                user_record = user_data[0]
                return User(**user_record)
            
            # Validate username uniqueness if updating username
            if "username" in update_data:
                existing_username = await execute_query(
                    "SELECT id FROM users WHERE username = $1 AND id != $2",
                    update_data["username"],
                    user_id
                )
                if existing_username:
                    raise ValueError("Username already taken")
            
            # Build dynamic update query
            set_clauses = []
            values = []
            param_count = 1
            
            for field, value in update_data.items():
                set_clauses.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
            
            # Add updated_at (handled by trigger, but explicit is better)
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.utcnow())
            param_count += 1
            
            # Add user_id for WHERE clause
            values.append(user_id)
            
            query = f"""
                UPDATE users 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
            """
            
            await execute_command(query, *values)
            
            # Log profile update activity
            await self._log_user_activity(
                user_id,
                "profile_update",
                {"updated_fields": list(update_data.keys())}
            )
            
            # Return updated user
            user_data = await execute_query("SELECT * FROM users WHERE id = $1", user_id)
            user_record = user_data[0]
            
            logger.info(f"✅ User profile updated: {user_id}")
            return User(**user_record)
            
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {str(e)}")
            raise Exception(f"Profile update failed: {str(e)}")

    async def list_users(self, skip: int = 0, limit: int = 100, filters: Dict[str, Any] = None) -> List[User]:
        """List users with optional filtering (admin function)"""
        try:
            # Base query
            base_query = "SELECT * FROM users"
            conditions = []
            values = []
            param_count = 1
            
            # Apply filters if provided
            if filters:
                if filters.get("is_active") is not None:
                    conditions.append(f"is_active = ${param_count}")
                    values.append(filters["is_active"])
                    param_count += 1
                
                if filters.get("is_admin") is not None:
                    conditions.append(f"is_admin = ${param_count}")
                    values.append(filters["is_admin"])
                    param_count += 1
                
                if filters.get("created_after"):
                    conditions.append(f"created_at > ${param_count}")
                    values.append(filters["created_after"])
                    param_count += 1
                
                if filters.get("wallet_address"):
                    conditions.append(f"wallet_address ILIKE ${param_count}")
                    values.append(f"%{filters['wallet_address']}%")
                    param_count += 1
            
            # Build final query
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            
            base_query += f" ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
            values.extend([limit, skip])
            
            users_data = await execute_query(base_query, *values)
            
            return [User(**user_record) for user_record in users_data]
            
        except Exception as e:
            logger.error(f"Failed to list users: {str(e)}")
            raise Exception(f"Failed to list users: {str(e)}")

    async def deactivate_user(self, user_id: str, admin_user_id: str) -> bool:
        """Deactivate a user account (admin function)"""
        try:
            # Check if admin user has permission
            admin_check = await execute_query(
                "SELECT is_admin FROM users WHERE id = $1 AND is_admin = TRUE",
                admin_user_id
            )
            
            if not admin_check:
                raise Exception("Insufficient permissions")
            
            # Deactivate user
            result = await execute_command(
                "UPDATE users SET is_active = FALSE, updated_at = $1 WHERE id = $2",
                datetime.utcnow(),
                user_id
            )
            
            # Log admin action
            await self._log_user_activity(
                admin_user_id,
                "admin_user_deactivated",
                {"target_user_id": user_id}
            )
            
            logger.info(f"✅ User deactivated: {user_id} by admin: {admin_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deactivate user {user_id}: {str(e)}")
            raise Exception(f"User deactivation failed: {str(e)}")

    async def check_rate_limit(self, user_id: str, action: str) -> bool:
        """Check if user has exceeded rate limits for specific actions"""
        try:
            # Check recent actions count
            recent_actions = await execute_query(
                """SELECT COUNT(*) as count FROM user_activities 
                   WHERE user_id = $1 AND action = $2 AND timestamp > $3""",
                user_id,
                action,
                datetime.utcnow() - timedelta(minutes=settings.rate_limit_window // 60)
            )
            
            count = recent_actions[0]["count"] if recent_actions else 0
            
            # Define action-specific limits
            action_limits = {
                "login": 10,
                "profile_update": 5,
                "data_refresh": 3,
                "token_balance_check": 50,
                "nft_view": 30
            }
            
            limit = action_limits.get(action, settings.rate_limit_requests)
            
            if count >= limit:
                logger.warning(f"Rate limit exceeded for user {user_id}, action: {action}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            # In case of error, allow the action (fail open)
            return True

    async def _log_user_activity(
        self, 
        user_id: str, 
        action: str, 
        metadata: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log user activity for analytics and security"""
        try:
            await execute_command(
                """INSERT INTO user_activities 
                   (user_id, action, metadata, ip_address, user_agent, timestamp)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                user_id,
                action,
                metadata,
                ip_address,
                user_agent,
                datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Failed to log user activity: {str(e)}")

    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active sessions for a user"""
        try:
            # Get recent login activities
            sessions = await execute_query(
                """SELECT DISTINCT ip_address, user_agent, timestamp
                   FROM user_activities 
                   WHERE user_id = $1 AND action = 'login'
                   AND timestamp > $2
                   ORDER BY timestamp DESC
                   LIMIT 10""",
                user_id,
                datetime.utcnow() - timedelta(days=7)
            )
            
            return [
                {
                    "ip_address": session["ip_address"],
                    "user_agent": session["user_agent"],
                    "last_seen": session["timestamp"].isoformat() if session["timestamp"] else None
                }
                for session in sessions
            ]
            
        except Exception as e:
            logger.error(f"Failed to get user sessions: {str(e)}")
            return []

    def generate_api_key(self, user_id: str) -> str:
        """Generate API key for programmatic access"""
        # Create a secure API key
        api_key_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().timestamp(),
            "random": secrets.token_hex(16)
        }
        
        # Create hash of the data
        api_key_string = f"{user_id}_{api_key_data['created_at']}_{api_key_data['random']}"
        api_key_hash = hashlib.sha256(api_key_string.encode()).hexdigest()
        
        # Format as API key
        api_key = f"sr_{api_key_hash[:32]}"
        
        logger.info(f"✅ API key generated for user: {user_id}")
        return api_key

    async def verify_api_key(self, api_key: str) -> Optional[str]:
        """Verify API key and return user ID"""
        try:
            if not api_key.startswith("sr_"):
                return None
            
            # In a production system, you'd store and verify API keys in database
            # This is a simplified implementation
            
            # For now, we'll use JWT-based API keys instead
            # You can extend this to use a proper API key system
            
            return None
            
        except Exception as e:
            logger.error(f"API key verification failed: {str(e)}")
            return None
 
