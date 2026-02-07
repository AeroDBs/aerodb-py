# Examples - aerodb-py

Real-world usage examples for common scenarios.

## Table of Contents

- [Authentication & User Management](#authentication--user-management)
- [CRUD Operations](#crud-operations)
- [Real-time Subscriptions](#real-time-subscriptions)
- [File Storage](#file-storage)
- [Advanced Queries](#advanced-queries)
- [Full Applications](#full-applications)

---

## Authentication & User Management

### Basic Sign Up Flow

```python
import asyncio
from aerodb import AeroDBClient

async def sign_up_flow():
    async with AeroDBClient(url="https://api.aerodb.com") as client:
        result = await client.auth.sign_up(
            email="user@example.com",
            password="securepassword123"
        )
        
        if result.error:
            print(f"Sign up failed: {result.error.message}")
            return
        
        print(f"Welcome! {result.data.user.email}")

asyncio.run(sign_up_flow())
```

### Persistent Auth Session

```python
async def check_session():
    async with AeroDBClient(url="...") as client:
        result = await client.auth.get_user()
        
        if result.data:
            print(f"Already logged in: {result.data.email}")
            return True
        else:
            print("Not logged in")
            return False
```

---

## CRUD Operations

### Blog Post Management

```python
from typing import TypedDict, Optional
from datetime import datetime

class Post(TypedDict):
    id: str
    title: str
    content: str
    author_id: str
    published: bool
    created_at: str

async def manage_posts(client: AeroDBClient, user_id: str):
    # Create
    result = await client.from_("posts").insert({
        "title": "Getting Started with AeroDB",
        "content": "This is my first post...",
        "author_id": user_id,
        "published": False
    })
    new_post = result.data[0]
    
    # Read
    result = await (
        client.from_("posts")
        .select("*")
        .eq("author_id", user_id)
        .order("created_at", ascending=False)
        .limit(10)
        .execute()
    )
    posts = result.data
    
    # Update
    await (
        client.from_("posts")
        .eq("id", new_post["id"])
        .update({"published": True})
    )
    
    # Delete
    await (
        client.from_("posts")
        .eq("id", new_post["id"])
        .delete()
    )
```

### Batch Operations

```python
async def create_multiple_posts(client: AeroDBClient, user_id: str):
    new_posts = [
        {"title": "Post 1", "content": "...", "author_id": user_id},
        {"title": "Post 2", "content": "...", "author_id": user_id},
        {"title": "Post 3", "content": "...", "author_id": user_id},
    ]
    
    result = await client.from_("posts").insert(new_posts)
    print(f"Inserted {len(result.data)} posts")
```

---

## Real-time Subscriptions

### Live Comment Feed

```python
import asyncio

async def on_new_comment(payload):
    new_comment = payload.new
    print(f"New comment from {new_comment['author']}: {new_comment['text']}")

async def live_comments(client: AeroDBClient, post_id: str):
    channel = client.channel(f"comments:post:{post_id}")
    await channel.on("INSERT", on_new_comment).subscribe()
    
    # Keep connection alive
    try:
        await asyncio.sleep(3600)  # 1 hour
    finally:
        await channel.unsubscribe()
```

### Live User Presence

```python
async def track_presence(client: AeroDBClient, doc_id: str, user_id: str):
    async def on_user_join(payload):
        viewer = payload.new
        print(f"User {viewer['user_id']} joined")
    
    async def on_user_leave(payload):
        viewer = payload.old
        print(f"User {viewer['user_id']} left")
    
    channel = client.channel(f"presence:doc:{doc_id}")
    await channel.on("INSERT", on_user_join).on("DELETE", on_user_leave).subscribe()
    
    # Announce this user
    await client.from_("presence").insert({
        "user_id": user_id,
        "doc_id": doc_id,
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        await asyncio.sleep(3600)
    finally:
        await (
            client.from_("presence")
            .eq("user_id", user_id)
            .eq("doc_id", doc_id)
            .delete()
        )
        await channel.unsubscribe()
```

---

## File Storage

### Avatar Upload

```python
async def upload_avatar(client: AeroDBClient, user_id: str, file_path: str):
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    
    path = f"users/{user_id}/avatar.png"
    result = await client.storage.from_("avatars").upload(path, file_bytes)
    
    if result.error:
        print(f"Upload failed: {result.error.message}")
        return
    
    # Get public URL
    public_url = client.storage.from_("avatars").get_public_url(path)
    
    # Update user profile
    await client.from_("users").eq("id", user_id).update({
        "avatar_url": public_url
    })
    
    print(f"Avatar uploaded: {public_url}")
```

### Bulk File Upload with Progress

```python
from pathlib import Path

async def upload_directory(client: AeroDBClient, dir_path: str):
    files = list(Path(dir_path).glob("*"))
    total = len(files)
    completed = 0
    
    for file_path in files:
        if not file_path.is_file():
            continue
        
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        
        path = f"uploads/{int(datetime.now().timestamp())}-{file_path.name}"
        result = await client.storage.from_("documents").upload(path, file_bytes)
        
        if result.error:
            print(f"Failed to upload {file_path.name}: {result.error.message}")
            continue
        
        completed += 1
        print(f"Progress: {completed}/{total} ({(completed/total)*100:.1f}%)")
    
    print(f"Uploaded {completed}/{total} files")
```

---

## Advanced Queries

### Search with Pagination

```python
async def search_posts(
    client: AeroDBClient,
    query: str,
    page: int = 1,
    per_page: int = 20
):
    result = await (
        client.from_("posts")
        .select("id, title, content, created_at, author:users(name)")
        .ilike("title", f"%{query}%")
        .eq("published", True)
        .order("created_at", ascending=False)
        .offset((page - 1) * per_page)
        .limit(per_page)
        .execute()
    )
    
    return result.data
```

### Complex Filtering

```python
from datetime import datetime, timedelta

async def get_active_users(client: AeroDBClient):
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    
    result = await (
        client.from_("users")
        .select("*, posts(count)")
        .eq("status", "active")
        .gte("created_at", thirty_days_ago)
        .execute()
    )
    
    # Filter in Python for complex logic
    qualified_users = [
        user for user in result.data or []
        if user.get("posts", [{}])[0].get("count", 0) >= 5
    ]
    
    return qualified_users
```

---

## Full Applications

### Chat Application

```python
from typing import List, Dict, Any

class ChatApp:
    def __init__(self, room_id: str, aerodb_url: str):
        self.client = AeroDBClient(url=aerodb_url)
        self.room_id = room_id
        self.channel = None
    
    async def init(self):
        # Subscribe to new messages
        self.channel = self.client.channel(f"messages:room:{self.room_id}")
        await self.channel.on("INSERT", self.on_message).subscribe()
        
        # Load message history
        result = await (
            self.client.from_("messages")
            .select("*, author:users(name, avatar_url)")
            .eq("room_id", self.room_id)
            .order("created_at", ascending=True)
            .limit(100)
            .execute()
        )
        
        for msg in result.data or []:
            self.display_message(msg)
    
    async def on_message(self, payload):
        self.display_message(payload.new)
    
    async def send_message(self, text: str, user_id: str):
        await self.client.from_("messages").insert({
            "room_id": self.room_id,
            "author_id": user_id,
            "text": text,
            "created_at": datetime.now().isoformat()
        })
    
    def display_message(self, msg: Dict[str, Any]):
        print(f"{msg.get('author', {}).get('name', 'Unknown')}: {msg['text']}")
    
    async def cleanup(self):
        if self.channel:
            await self.channel.unsubscribe()
        await self.client.__aexit__(None, None, None)

# Usage
async def main():
    chat = ChatApp("room-abc", "https://api.aerodb.com")
    async with chat.client:
        await chat.init()
        await chat.send_message("Hello, world!", "user-123")
        await asyncio.sleep(10)
        await chat.cleanup()

asyncio.run(main())
```

### Todo App

```python
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class Todo:
    id: str
    text: str
    completed: bool
    user_id: str

class TodoApp:
    def __init__(self, client: AeroDBClient):
        self.client = client
        self.cache: Dict[str, Todo] = {}
    
    async def load_todos(self) -> List[Todo]:
        result = await (
            self.client.from_("todos")
            .select("*")
            .order("created_at", ascending=False)
            .execute()
        )
        
        if result.data:
            for todo_dict in result.data:
                todo = Todo(**todo_dict)
                self.cache[todo.id] = todo
        
        return list(self.cache.values())
    
    async def add_todo(self, text: str, user_id: str):
        result = await self.client.from_("todos").insert({
            "text": text,
            "completed": False,
            "user_id": user_id
        })
        
        if result.data:
            todo = Todo(**result.data[0])
            self.cache[todo.id] = todo
        
        return result.data
    
    async def toggle_todo(self, todo_id: str):
        todo = self.cache.get(todo_id)
        if not todo:
            return
        
        todo.completed = not todo.completed
        
        await (
            self.client.from_("todos")
            .eq("id", todo_id)
            .update({"completed": todo.completed})
        )
    
    async def delete_todo(self, todo_id: str):
        await (
            self.client.from_("todos")
            .eq("id", todo_id)
            .delete()
        )
        
        del self.cache[todo_id]

# Usage
async def main():
    async with AeroDBClient(url="...") as client:
        app = TodoApp(client)
        
        # Load existing todos
        todos = await app.load_todos()
        print(f"Loaded {len(todos)} todos")
        
        # Add new todo
        await app.add_todo("Learn AeroDB", "user-123")
        
        # Toggle and delete
        if todos:
            await app.toggle_todo(todos[0].id)
            await app.delete_todo(todos[0].id)

asyncio.run(main())
```

## More Examples

For more examples, see:
- [GitHub Examples Directory](https://github.com/aerodb/aerodb-py/tree/main/examples)
- [AeroDB Documentation](https://docs.aerodb.com/examples)
- [Community Recipes](https://github.com/aerodb/community-recipes)
