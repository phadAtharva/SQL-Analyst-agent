from dotenv import load_dotenv
import psycopg2
import os

load_dotenv()


PG_DB_URL = os.getenv("PG_DB_URL")

class Database:
    
    def __init__(self):
        try :
          self.conn = psycopg2.connect(PG_DB_URL)
        except Exception as e:
            print(f"Error connecting to the database: {e}")
            self.conn = None
        
    def schema_details(self,schema_name):
        schema_info_context=""
        conn = self.conn
        cursor = conn.cursor()

        try :
          schema_info_context=f"Schema: {schema_name}\n"
          cursor.execute(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name}'")
          tables_list = cursor.fetchall()


          for table in tables_list:
              schema_info_context += f"Table: {table[0]}\n"
              cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = '{schema_name}' AND table_name = '{table[0]}'")
              columns_list = cursor.fetchall()
              for column in columns_list:
                  schema_info_context += f"    Column name: {column[0]}, DataType: {column[1]}\n"

              cursor.execute(f"SELECT * FROM {schema_name}.{table[0]} LIMIT 5")
              rows = cursor.fetchall()
              for row in rows:
                  schema_info_context += f"    Sample Data Row: {row}\n"
                  
        except Exception as e:
            print(f"Error fetching schema details: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()  
        return schema_info_context
    
    def execute_query(self, query):
        result = None
        conn = self.conn
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            result = cursor.fetchall()
        except Exception as e:
            print(f"Error executing query: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        return str(result)

    

obj= Database()

result= obj.schema_details("public")
  
with open("schema_details.txt", "w") as f:
    f.write(result)


    
    



    


