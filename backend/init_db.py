import os
import asyncio
from supabase import create_client
from dotenv import load_dotenv
from schemas import SUPABASE_SCHEMA

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")


async def create_tables():
    """Create all required tables in Supabase."""
    print("Creating tables...")
    
    # Initialize Supabase client
    supabase = create_client(supabase_url, supabase_key)
    
    # Create tables
    for table in SUPABASE_SCHEMA["tables"]:
        table_name = table["name"]
        print(f"Creating table: {table_name}")
        
        # Construct the SQL statement
        columns = []
        for column in table["columns"]:
            column_def = f"{column['name']} {column['type']}"
            
            if column.get("primaryKey"):
                column_def += " PRIMARY KEY"
            
            if column.get("notNull"):
                column_def += " NOT NULL"
            
            if column.get("unique"):
                column_def += " UNIQUE"
            
            if column.get("default"):
                column_def += f" DEFAULT {column['default']}"
            
            if column.get("references"):
                ref = column["references"]
                column_def += f" REFERENCES {ref['table']}({ref['column']})"
            
            columns.append(column_def)
        
        create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)});"
        
        # Execute the statement
        try:
            response = supabase.table(table_name).select("count(*)").limit(1).execute()
            print(f"Table {table_name} already exists")
        except Exception:
            # Table doesn't exist, create it
            response = await supabase.postgrest.schema("public").execute(create_table_sql)
            print(f"Created table {table_name}")
    
    # Create indexes
    print("Creating indexes...")
    for index in SUPABASE_SCHEMA["indexes"]:
        table_name = index["table"]
        columns = ",".join(index["columns"])
        method = index["method"]
        options = index.get("options", "")
        
        index_name = f"idx_{table_name}_{'_'.join(index['columns'])}"
        create_index_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} USING {method} ({columns})"
        
        if options:
            create_index_sql += f" {options}"
        
        # Execute the statement
        try:
            response = await supabase.postgrest.schema("public").execute(create_index_sql)
            print(f"Created index {index_name}")
        except Exception as e:
            print(f"Error creating index {index_name}: {str(e)}")
    
    # Create row-level security policies
    print("Creating RLS policies...")
    for policy in SUPABASE_SCHEMA["policies"]:
        table_name = policy["table"]
        policy_name = policy["name"]
        definition = policy["definition"]
        using_expr = policy["using"]
        check_expr = policy.get("check")
        
        # Enable RLS on the table
        enable_rls_sql = f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"
        
        # Create the policy
        create_policy_sql = f"CREATE POLICY IF NOT EXISTS {policy_name} ON {table_name} FOR {definition} USING ({using_expr})"
        
        if check_expr:
            create_policy_sql += f" WITH CHECK ({check_expr})"
        
        # Execute the statements
        try:
            response = await supabase.postgrest.schema("public").execute(enable_rls_sql)
            print(f"Enabled RLS on {table_name}")
            
            response = await supabase.postgrest.schema("public").execute(create_policy_sql)
            print(f"Created policy {policy_name} on {table_name}")
        except Exception as e:
            print(f"Error creating policy {policy_name} on {table_name}: {str(e)}")
    
    print("Database initialization complete!")


async def main():
    await create_tables()


if __name__ == "__main__":
    asyncio.run(main())
