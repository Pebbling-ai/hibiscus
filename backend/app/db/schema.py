# Supabase Schema Definition
SUPABASE_SCHEMA = {
    "tables": [
        {
            "name": "users",
            "columns": [
                {"name": "id", "type": "uuid", "primaryKey": True},
                {"name": "email", "type": "text", "notNull": True, "unique": True},
                {"name": "full_name", "type": "text", "notNull": True},
                {"name": "created_at", "type": "timestamp with time zone", "notNull": True, "default": "now()"},
                {"name": "updated_at", "type": "timestamp with time zone"},
            ]
        },
        {
            "name": "api_keys",
            "columns": [
                {"name": "id", "type": "uuid", "primaryKey": True, "default": "gen_random_uuid()"},
                {"name": "user_id", "type": "uuid", "notNull": True, "references": {"table": "users", "column": "id"}},
                {"name": "key", "type": "text", "notNull": True, "unique": True},
                {"name": "name", "type": "text", "notNull": True},
                {"name": "created_at", "type": "timestamp with time zone", "notNull": True, "default": "now()"},
                {"name": "last_used_at", "type": "timestamp with time zone"},
                {"name": "expires_at", "type": "timestamp with time zone"},
            ]
        },
        {
            "name": "agents",
            "columns": [
                {"name": "id", "type": "uuid", "primaryKey": True, "default": "gen_random_uuid()"},
                {"name": "owner_id", "type": "uuid", "notNull": True, "references": {"table": "users", "column": "id"}},
                {"name": "name", "type": "text", "notNull": True},
                {"name": "description", "type": "text", "notNull": True},
                {"name": "category", "type": "text", "notNull": True},
                {"name": "capabilities", "type": "jsonb", "notNull": True, "default": "[]"},
                {"name": "api_endpoint", "type": "text"},
                {"name": "website_url", "type": "text"},
                {"name": "logo_url", "type": "text"},
                {"name": "is_federated", "type": "boolean", "notNull": True, "default": False},
                {"name": "federation_source", "type": "text"},
                {"name": "created_at", "type": "timestamp with time zone", "notNull": True, "default": "now()"},
                {"name": "updated_at", "type": "timestamp with time zone", "notNull": True, "default": "now()"},
            ]
        },
        {
            "name": "federated_registries",
            "columns": [
                {"name": "id", "type": "uuid", "primaryKey": True, "default": "gen_random_uuid()"},
                {"name": "name", "type": "text", "notNull": True},
                {"name": "url", "type": "text", "notNull": True, "unique": True},
                {"name": "api_key", "type": "text"},
                {"name": "created_at", "type": "timestamp with time zone", "notNull": True, "default": "now()"},
                {"name": "last_synced_at", "type": "timestamp with time zone"},
            ]
        }
    ],
    "indexes": [
        {"table": "agents", "columns": ["name"], "method": "btree"},
        {"table": "agents", "columns": ["category"], "method": "btree"},
        {"table": "agents", "columns": ["description"], "method": "gin", "options": "to_tsvector('english', description)"},
        {"table": "api_keys", "columns": ["user_id"], "method": "btree"},
    ],
    "policies": [
        {
            "table": "agents",
            "name": "agents_select_policy",
            "definition": "SELECT",
            "using": "TRUE",
            "check": "TRUE"
        },
        {
            "table": "agents",
            "name": "agents_insert_policy",
            "definition": "INSERT",
            "using": "auth.uid() = owner_id",
            "check": "auth.uid() = owner_id"
        },
        {
            "table": "agents",
            "name": "agents_update_policy",
            "definition": "UPDATE",
            "using": "auth.uid() = owner_id",
            "check": "auth.uid() = owner_id"
        },
        {
            "table": "agents",
            "name": "agents_delete_policy",
            "definition": "DELETE",
            "using": "auth.uid() = owner_id",
            "check": "auth.uid() = owner_id"
        },
        {
            "table": "api_keys",
            "name": "api_keys_select_policy",
            "definition": "SELECT",
            "using": "auth.uid() = user_id",
            "check": "auth.uid() = user_id"
        },
        {
            "table": "api_keys",
            "name": "api_keys_insert_policy",
            "definition": "INSERT",
            "using": "auth.uid() = user_id",
            "check": "auth.uid() = user_id"
        },
        {
            "table": "api_keys",
            "name": "api_keys_delete_policy",
            "definition": "DELETE",
            "using": "auth.uid() = user_id",
            "check": "auth.uid() = user_id"
        }
    ]
}
