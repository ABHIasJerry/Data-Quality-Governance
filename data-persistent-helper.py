import json
import os
import pickle
import shutil
import subprocess
import time
import traceback

import cv2
import paramiko
import requests
from zipfile import ZipFile

import serial
from packaging import version

# No longer supported inside requests module [disabled]
# from requests.packages.urllib3.exceptions import InsecureRequestWarning
# requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

import urllib3
from urllib3.exceptions import InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import yaml
import pandas
from requests.auth import HTTPBasicAuth
from tqdm import tqdm
from uiautomator import device, JsonRPCError

from DMAutomatedTest.DMHelper.Connector import SSHConnector, DBConnector
from psycopg2 import extensions

from DMAutomatedTest.DMHelper.TestCaseHelper import TestCaseHelper
from DMAutomatedTest.DataPersistent import Constants


def get_database_columns_value(table_name, columns_name):
    pass


class DataHelper:
    """
    Data Helper class contain all supportive function
    """

 # ****************************** YAML DB verification ******************************
  def table_exist(self, data):
      """

      Args:
          data:
      """
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      if table_name is None:
          return False, 'table name not defined'
      else:
          table_exist = f'''select count(*) from information_schema.tables where table_name= '{table_name}' AND table_schema='{schema}' '''
          cursor = self.pg_db_connector.db_connection.cursor()
          cursor.execute(table_exist)
          data = cursor.fetchall()
          if 1 == data[0][0]:
              return True, ''
          else:
              return False, f'Table [{table_name}] not found'

  def table_not_exist(self, data):
      """

      Args:
          data:
      """
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      if table_name is None:
          return False, 'table name not defined'
      else:
          table_exist = f'''select count(*) from information_schema.tables where table_name= '{table_name}' AND table_schema='{schema}' '''
          cursor = self.pg_db_connector.db_connection.cursor()
          cursor.execute(table_exist)
          data = cursor.fetchall()
          if 0 == data[0][0]:
              return True, ''
          else:
              return False, f'Table [{table_name}] found'

  def table_properties(self, data):
      """

      Args:
          data:

      Returns:

      """

      fail_result = []
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      properties = data.get('properties')

      if table_name is None:
          return False, 'table name not defined'
      elif properties is None:
          return False, 'properties value not defined'

      for function_property in properties:
          prop, expected_value = tuple(function_property.items())[0]
          if prop == 'owner':
              owner_check_query = f'''select tableowner 
                                      from pg_catalog.pg_tables
                                      where schemaname = '{schema}'
                                      and tablename = '{table_name}';'''
              data, col = self.pg_db_connector.run_select_query(owner_check_query)
              if len(data) > 0:
                  actual_value = data[0][0]
                  if actual_value != expected_value:
                      fail_result.append({'property name': prop, 'actual': actual_value, 'expected': expected_value})
              else:
                  fail_result.append(
                      {'property name': prop, 'actual': f'table {table_name} not found', 'expected': expected_value})

      if len(fail_result) == 0:
          return True, ''
      else:
          return False, f'failed to verify : {json.dumps(fail_result)}'

  def column_exist(self, data):
      """

      Args:
          data:
      """
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      column_name = data.get('column name')
      if table_name is None:
          return False, 'table name not defined'
      elif column_name is None:
          return False, 'column name not defined'
      else:
          column_exist = f'''select count(*) from information_schema.columns where table_name= '{table_name}' AND table_schema='{schema}' AND column_name='{column_name}' '''
          cursor = self.pg_db_connector.db_connection.cursor()
          cursor.execute(column_exist)
          data = cursor.fetchall()
          if 1 == data[0][0]:
              return True, ''
          else:
              return False, f'Column [{column_name}] not found'

  def column_not_exist(self, data):
      """

      Args:
          data:
      """
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      column_name = data.get('column name')
      if table_name is None:
          return False, 'table name not defined'
      elif column_name is None:
          return False, 'column name not defined'
      else:
          column_exist = f'''select count(*) from information_schema.columns where table_name= '{table_name}' AND table_schema='{schema}' AND column_name='{column_name}' '''
          cursor = self.pg_db_connector.db_connection.cursor()
          cursor.execute(column_exist)
          data = cursor.fetchall()
          if 0 == data[0][0]:
              return True, ''
          else:
              return False, f'Column [{column_name}] found'

  def column_value(self, data):
      """

      Args:
          data:
      """
      fail_result = []
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      column_name = data.get('column name')
      value = data.get('value')
      condition = data.get('conditions')
      verify_all = data.get('verify all rows', True)

      column_query = None

      if table_name is None:
          return False, 'table name not defined'
      elif column_name is None:
          return False, 'column name not defined'
      elif value is None:
          return False, 'expected value not defined'
      elif condition is not None:
          condition_concat = condition.replace('|', 'OR').replace('&', 'AND')
          column_query = f'''select * from {schema}.{table_name} where {condition_concat}'''

      if column_query is None:
          column_query = f'''select * from {schema}.{table_name}'''

      try:
          data, columns = self.pg_db_connector.run_select_query(column_query)
      except Exception as Err:
          return False, f'{str(Err)}'

      if len(data) != 0:
          if not verify_all:
              data = data[:1]
          for row in data:
              if column_name in columns:
                  actual_value = str(row[columns.index(column_name)])
                  if actual_value != value:
                      fail_result.append({'actual': actual_value, 'expected': value})
              else:
                  fail_result.append({'actual': f'column [{column_name}] not found', 'expected': value})
      if len(fail_result) == 0:
          return True, ''
      else:
          return False, f'failed to verify : {json.dumps(fail_result)}'

  def column_value_multiple(self, data):
      """

      Args:
          data:
      """
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      column_name = data.get('column name')
      column_values = data.get('column values')

      if table_name is None:
          return False, 'table name not defined'
      elif column_name is None:
          return False, 'column name not defined'
      elif column_values is None:
          return False, 'expected values not defined'

      column_query = f'''select {column_name} from {schema}.{table_name} '''
      try:
          data, columns = self.pg_db_connector.run_select_query(column_query)
      except Exception as Err:
          return False, f'{str(Err)}'

      if len(data) != 0:
          column_values_db = [i[0] for i in data]
          column_value_not_present = [col for col in column_values if col not in column_values_db]
          if len(column_value_not_present) == 0:
              return True, ''
          else:
              return False, f'failed to verify : values not found : {column_value_not_present}'
      return False, f'failed to verify : data not found for col {column_name}'

  def column_properties(self, data):
      """

      Args:
          data:
      """
      fail_result = []
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      column_name = data.get('column name')
      properties = data.get('properties')

      properties_list = ['is_nullable', 'data_type', 'is_identity', 'column_default']

      if table_name is None:
          return False, 'table name not defined'
      elif column_name is None:
          return False, 'column name not defined'
      elif properties is None:
          return False, 'properties value not defined'

      column_select = ','.join(properties_list)

      query = f'''select {column_select} from information_schema.columns where 
                  table_schema='{schema}' and table_name='{table_name}' and column_name='{column_name}' '''
      data, columns = self.pg_db_connector.run_select_query(query)

      if len(data) != 1:
          return False, f'failed to verify : Column [{column_name}] not found'

      for column_property in properties:
          prop, expected_value = tuple(column_property.items())[0]
          actual_value = data[0][columns.index(prop)]

          if actual_value != expected_value:
              fail_result.append({'property name': prop, 'actual': actual_value, 'expected': expected_value})

      if len(fail_result) == 0:
          return True, ''
      else:
          return False, f'failed to verify : {json.dumps(fail_result)}'

  def column_update_from_table(self, data):
      """

      Args:
          data:
      """
      fail_result = []
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      column_name = data.get('column name')
      from_table = data.get('from table')
      from_column = data.get('from column')
      on_condition = data.get('on condition')

      if table_name is None:
          return False, 'table name not defined'
      elif column_name is None:
          return False, 'column name not defined'
      elif from_table is None:
          return False, 'from table not defined'
      elif from_column is None:
          return False, 'from column not defined'
      elif on_condition is None:
          return False, 'on condition not defined'

      first_col, second_col, condition = None, None, None
      if on_condition is not None:
          first_col = on_condition.get('first col')
          second_col = on_condition.get('second col')
          condition = on_condition.get('condition')
          if condition == 'equal':
              condition = '='
          elif condition == 'not equal':
              condition = '!='

      from_data_query = f'''select {from_column} from {schema}.{from_table}'''
      from_data, from_columns = self.pg_db_connector.run_select_query(from_data_query)
      for d in from_data:
          value_d = d[0]
          condition_value = d[from_columns.index(second_col)]
          main_data_query = f'''select {column_name} from {schema}.{table_name} where {first_col}{condition}{condition_value}'''
          main_data, main_columns = self.pg_db_connector.run_select_query(main_data_query)
          for m in main_data:
              value_m = m[0]
              if value_m != value_d:
                  fail_result.append({'Actual': value_m, 'Expected': value_d})

      if len(fail_result) > 0:
          return False, f'Failed to validate fields {fail_result}'
      return True, ''

  def row_value_multiple(self, data):
      """

      Args:
          data:
      """
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      column_names = data.get('columns name')
      row_values = data.get('row values')

      if table_name is None:
          return False, 'table name not defined'
      elif column_names is None:
          return False, 'column names not defined'
      elif row_values is None:
          return False, 'expected values for row values not defined'

      failed_entries = []
      for index, item in row_values.items():
          condition = ''
          counter = 0
          for col, value in zip(column_names, item):
              counter += 1
              if isinstance(value, str) and '@fromtable.' in value:
                  ft_table_name, ft_column_name, ft_column_value, ft_select_column = value.replace('@fromtable.',
                                                                                                   '').split('.')
                  query_selection = f''' select {ft_select_column} from {ft_table_name} where {ft_column_name}='{ft_column_value}'  '''
                  ft_data, ft_columns = self.pg_db_connector.run_select_query(query_selection)
                  if len(ft_data) > 0:
                      value = ft_data[0][0]

              if counter == len(column_names):
                  condition += f"{col}='{value}' "
              else:
                  condition += f"{col}='{value}' and "

          query = f'''  select count(*) from {schema}.{table_name} where {condition} '''
          main_data, main_columns = self.pg_db_connector.run_select_query(query)
          if not main_data[0][0] > 0:
              temp = {'index': index, 'data': str(tuple(item))}
              failed_entries.append(temp)

      if len(failed_entries) > 0:
          return False, f'Failed to validate rows : {failed_entries}'
      return True, ''

  def row_value_multiple_delete(self, data):
      """

      Args:
          data:
      """
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      column_names = data.get('columns name')
      row_values = data.get('row values')

      if table_name is None:
          return False, 'table name not defined'
      elif column_names is None:
          return False, 'column names not defined'
      elif row_values is None:
          return False, 'expected values for row values not defined'

      failed_entries = []
      for index, item in row_values.items():
          condition = ''
          counter = 0
          for col, value in zip(column_names, item):
              counter += 1
              if isinstance(value, str) and '@fromtable.' in value:
                  ft_table_name, ft_column_name, ft_column_value, ft_select_column = value.replace('@fromtable.',
                                                                                                   '').split('.')
                  query_selection = f''' select {ft_select_column} from {ft_table_name} where {ft_column_name}='{ft_column_value}'  '''
                  ft_data, ft_columns = self.pg_db_connector.run_select_query(query_selection)
                  if len(ft_data) > 0:
                      value = ft_data[0][0]

              if counter == len(column_names):
                  condition += f"{col}='{value}' "
              else:
                  condition += f"{col}='{value}' and "

          query = f'''  select count(*) from {schema}.{table_name} where {condition} '''
          main_data, main_columns = self.pg_db_connector.run_select_query(query)
          if main_data[0][0] != 0:
              temp = {'index': index, 'data': str(tuple(item))}
              failed_entries.append(temp)

      if len(failed_entries) > 0:
          return False, f'Failed to validate deleted rows : {failed_entries}'
      return True, ''

  def sequence_not_exist(self, data):
      """

      Args:
          data:
      """
      schema = data.get('schema', 'public')
      sequence_name = data.get('sequence name')
      if sequence_name is None:
          return False, 'sequence name not defined'
      else:
          column_exist = f'''select count(*) from information_schema.sequences where sequence_schema ='{schema}' AND sequence_name ='{sequence_name}' '''
          cursor = self.pg_db_connector.db_connection.cursor()
          cursor.execute(column_exist)
          data = cursor.fetchall()
          if 0 == data[0][0]:
              return True, ''
          else:
              return False, f'Sequence [{sequence_name}] found'

  def sequence_exist(self, data):
      """

      Args:
          data:
      """
      schema = data.get('schema', 'public')
      sequence_name = data.get('sequence name')
      if sequence_name is None:
          return False, 'sequence name not defined'
      else:
          column_exist = f'''select count(*) from information_schema.sequences where sequence_schema ='{schema}' AND sequence_name ='{sequence_name}' '''
          cursor = self.pg_db_connector.db_connection.cursor()
          cursor.execute(column_exist)
          data = cursor.fetchall()
          if 1 == data[0][0]:
              return True, ''
          else:
              return False, f'Sequence [{sequence_name}] not found'

  def sequence_current_value(self, data):
      """

      Args:
          data:
      """
      schema = data.get('schema', 'public')
      sequence_name = data.get('sequence name')
      expected_value = data.get('current value')
      if sequence_name is None:
          return False, 'sequence name not defined'
      elif expected_value is None:
          return False, 'sequence expected current value not defined'
      else:
          if self.sequence_exist({'sequence name': sequence_name})[0]:
              current_value = f'''select last_value from {schema}.{sequence_name};'''
              cursor = self.pg_db_connector.db_connection.cursor()
              cursor.execute(current_value)
              data = cursor.fetchall()
              current_value = data[0][0]
              if expected_value == current_value:
                  return True, ''
              return False, f'Failed :  Expected  value : {expected_value}, Actual value : {current_value}'
          return False, f'Failed :  sequence is not exist'

  def sequence_owner(self, data):
      """

      Args:
          data:

      Returns:

      """
      schema = data.get('schema', 'public')
      seq_name = data.get('sequence name')
      owner = data.get('owner')
      table_name = data.get('table name')
      column_name = data.get('column name')

      if seq_name is None:
          return False, 'sequence  name not defined'
      elif owner is None and table_name is None and column_name is None:
          return False, 'owner value not defined'

      owner_check_query = f'''SELECT count(*)
                              FROM pg_class c, pg_user u
                              WHERE c.relowner = u.usesysid and c.relkind = 'S'
                              AND relnamespace IN (
                                                      SELECT oid
                                                        FROM pg_namespace
                                                       WHERE nspname NOT LIKE 'pg_%'
                                                         AND nspname != 'information_schema'
                                                      ) and relname='{seq_name}' and u.usename='{owner}'  '''

      if column_name is not None:
          owner_check_query = '''SELECT count(*)
                                  FROM pg_class AS seqclass
                                  JOIN pg_depend AS dep
                                  ON ( seqclass.relfilenode = dep.objid )
                                  JOIN pg_class AS depclass
                                  ON ( dep.refobjid = depclass.relfilenode )
                                  JOIN pg_attribute AS attrib
                                  ON ( attrib.attnum = dep.refobjsubid
                                  AND attrib.attrelid = dep.refobjid )
                                  WHERE seqclass.relname = 'variety_harvesting_map_id_seq'
                                  AND depclass.relname = 'variety_harvesting_map'
                                  AND attrib.attname = 'id'
                                  AND seqclass.relkind = 'S';
                              '''

      data, col = self.pg_db_connector.run_select_query(owner_check_query)
      if len(data) > 0:
          if 0 == data[0][0]:
              return False, f'Owner name not match Expected [{owner}]'
          else:
              return True, ''
      return False, f'Sequence not found [{seq_name}]'

  def constraint_not_exist(self, data):
      """

      Args:
          data:

      Returns:

      """
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      column_name = data.get('column name')
      constraint_name = data.get('constraint name')
      if table_name is None:
          return False, 'table name not defined'
      if constraint_name is None:
          return False, 'constraint name not defined'
      else:
          if column_name is not None:
              constraint_exist = f'''SELECT count(*) FROM information_schema.constraint_column_usage where constraint_schema='{schema}' and table_name='{table_name}' and constraint_name='{constraint_name}' '''
          else:
              constraint_exist = f'''SELECT count(*) FROM information_schema.constraint_table_usage where constraint_schema='{schema}' and table_name='{table_name}' and constraint_name='{constraint_name}' '''

          cursor = self.pg_db_connector.db_connection.cursor()
          cursor.execute(constraint_exist)
          data = cursor.fetchall()
          if 0 == data[0][0]:
              return True, ''
          else:
              return False, f'Constraint [{constraint_name}] found'

  def constraint_exist(self, data):
      """

      Args:
          data:

      Returns:

      """
      schema = data.get('schema', 'public')
      table_name = data.get('table name')
      column_name = data.get('column name')
      constraint_name = data.get('constraint name')
      if table_name is None:
          return False, 'table name not defined'
      if constraint_name is None:
          return False, 'constraint name not defined'
      else:
          # if column_name is not None:
          #     constraint_exist = f'''SELECT count(*) FROM information_schema.constraint_column_usage where constraint_schema='{schema}' and table_name='{table_name}' and constraint_name='{constraint_name}' '''
          # else:
          #     constraint_exist = f'''SELECT count(*) FROM information_schema.constraint_table_usage where constraint_schema='{schema}' and table_name='{table_name}' and constraint_name='{constraint_name}' '''
          constraint_exist = f'''SELECT count(*)
                                     FROM pg_catalog.pg_constraint con
                                          INNER JOIN pg_catalog.pg_class rel
                                                     ON rel.oid = con.conrelid
                                          INNER JOIN pg_catalog.pg_namespace nsp
                                                     ON nsp.oid = connamespace
                                     WHERE nsp.nspname = '{schema}'
                                           AND rel.relname = '{table_name}'
                                           and con.conname='{constraint_name}';'''
          cursor = self.pg_db_connector.db_connection.cursor()
          cursor.execute(constraint_exist)
          data = cursor.fetchall()
          if 1 == data[0][0]:
              return True, ''
          else:
              return False, f'Constraint [{constraint_name}] not found'

  def constraint_foreign_key(self, data):
      """

      Args:
          data:

      Returns:

      """
      fk_schema_name = data.get('fk schema', 'public')
      pk_schema_name = data.get('pk schema', 'public')
      fk_table_name = data.get('fk table name')
      fk_column_name = data.get('fk column name')
      pk_table_name = data.get('pk table name')
      pk_column_name = data.get('pk column name')
      constraint_name = data.get('constraint name')

      if constraint_name is None:
          return False, 'constraint name not defined'

      if fk_table_name is None:
          return False, 'fk table name not defined'
      elif fk_column_name is None:
          return False, 'fk column name not defined'
      elif pk_table_name is None:
          return False, 'pk table name not defined'
      elif pk_column_name is None:
          return False, 'pk column name not defined'

      constraint_query = f'''select kcu.table_schema as fk_schema,
                                  kcu.table_name as fk_table,
                                 rel_kcu.table_schema as pk_schema ,
                                 rel_kcu.table_name as pk_table,
                                 kcu.column_name as fk_column,
                                 rel_kcu.column_name as pk_column,
                                 kcu.constraint_name
                          from information_schema.table_constraints tco
                          join information_schema.key_column_usage kcu
                                    on tco.constraint_schema = kcu.constraint_schema
                                    and tco.constraint_name = kcu.constraint_name
                          join information_schema.referential_constraints rco
                                    on tco.constraint_schema = rco.constraint_schema
                                    and tco.constraint_name = rco.constraint_name
                          join information_schema.key_column_usage rel_kcu
                                    on rco.unique_constraint_schema = rel_kcu.constraint_schema
                                    and rco.unique_constraint_name = rel_kcu.constraint_name
                                    and kcu.ordinal_position = rel_kcu.ordinal_position
                          where tco.constraint_type = 'FOREIGN KEY' and tco.constraint_name='{constraint_name}'
                          order by kcu.table_schema,
                                   kcu.table_name,
                                   kcu.ordinal_position;
                          '''
      data, column = self.pg_db_connector.run_select_query(constraint_query)
      if len(data) > 0:
          failed_result = []
          fk_schema, fk_table, pk_schema, pk_table, fk_column, pk_column, constraint_name = data[0]
          if fk_schema != fk_schema_name and fk_table != fk_table_name:
              failed_result.append({'Field': 'schema.foreign_table',
                                    'Expected': f'{fk_schema_name}.{fk_table_name}',
                                    'Actual': f'{fk_schema}.{fk_table}'})
          if pk_schema != pk_schema_name and pk_table != pk_table_name:
              failed_result.append({'Field': 'schema.primary_table',
                                    'Expected': f'{pk_schema_name}.{pk_table_name}',
                                    'Actual': f'{pk_schema}.{pk_table}'})
          if pk_column != pk_column:
              failed_result.append({'Field': 'primary column',
                                    'Expected': f'{pk_column_name}',
                                    'Actual': f'{pk_column}'})
          if fk_column != fk_column:
              failed_result.append({'Field': 'foreign column',
                                    'Expected': f'{fk_column_name}',
                                    'Actual': f'{fk_column}'})

          if len(failed_result) > 0:
              return False, f'Failed to validate fields : {json.dumps(failed_result)}'
          else:
              return True, ''
      else:
          return False, f'Constraint {constraint_name} not exist'

  def function_exists(self, data):
      """

      Args:
          data:

      Returns:

      """

      schema = data.get('schema', 'public')
      function_name = data.get('function name')
      return_type = data.get('return type')
      language = data.get('language')

      if function_name is None:
          return False, 'function name is not defined'
      else:
          function_query = f"""select n.nspname as function_schema,
                                     p.proname as function_name,
                                     l.lanname as function_language,
                                     case when l.lanname = 'internal' then p.prosrc
                                          else pg_get_functiondef(p.oid)
                                          end as definition,
                                     pg_get_function_arguments(p.oid) as function_arguments,
                                     t.typname as return_type
                                      from pg_proc p
                                      left join pg_namespace n on p.pronamespace = n.oid
                                      left join pg_language l on p.prolang = l.oid
                                      left join pg_type t on t.oid = p.prorettype 
                                      where n.nspname not in ('pg_catalog', 'information_schema') and 
                                      n.nspname='{schema}' and 
                                      p.proname='{function_name}'
                                      order by function_schema,
                                               function_name;"""
          data, column = self.pg_db_connector.run_select_query(function_query)
          if len(data) > 0:
              function_data = data[0]
              failed = {}
              actual_return_type = function_data[column.index('return_type')]
              actual_language = function_data[column.index('function_language')]
              if actual_return_type != return_type:
                  failed['return type'] = {'actual': actual_return_type,
                                           'expected': return_type}
              if actual_language != language:
                  failed['language'] = {'actual': actual_language,
                                        'expected': language}
              if len(failed) > 0:
                  return False, f'Failed to validate : {failed}'
              else:
                  return True, ''
          else:
              return False, 'Postgres function not Found'

  def function_not_exists(self, data):
      """

      Args:
          data:

      Returns:

      """

      schema = data.get('schema', 'public')
      function_name = data.get('function name')

      if function_name is None:
          return False, 'function name is not defined'
      else:
          function_query = f"""select count(*)
                                      from pg_proc p
                                      left join pg_namespace n on p.pronamespace = n.oid
                                      left join pg_language l on p.prolang = l.oid
                                      left join pg_type t on t.oid = p.prorettype 
                                      where n.nspname not in ('pg_catalog', 'information_schema') and 
                                      n.nspname='{schema}' and 
                                      p.proname='{function_name}'
                                      order by function_schema,
                                               function_name;"""
          cursor = self.pg_db_connector.db_connection.cursor()
          cursor.execute(function_query)
          data = cursor.fetchall()
          return 1 == data[0][0], ''

  def function_properties(self, data):
      """

      Args:
          data:

      Returns:

      """

      fail_result = []
      schema = data.get('schema', 'public')
      function_name = data.get('function_name')
      properties = data.get('properties')

      if function_name is None:
          return False, 'function name not defined'
      elif properties is None:
          return False, 'properties value not defined'

      for function_property in properties:
          prop, expected_value = tuple(function_property.items())[0]
          if prop == 'owner':
              owner_check_query = f'''SELECT rolname FROM pg_catalog.pg_authid where oid = (
                                          SELECT proowner FROM pg_catalog.pg_namespace n
                                          JOIN pg_catalog.pg_proc p
                                          ON pronamespace=n.oid
                                          WHERE nspname='{schema}' and proname='{function_name}');'''
              data, col = self.pg_db_connector.run_select_query(owner_check_query)
              if len(data) > 0:
                  actual_value = data[0][0]
                  if actual_value != expected_value:
                      fail_result.append({'property name': prop, 'actual': actual_value, 'expected': expected_value})
              else:
                  fail_result.append(
                      {'property name': prop, 'actual': f'function {function_name} not found',
                       'expected': expected_value})

      if len(fail_result) == 0:
          return True, ''
      else:
          return False, f'failed to verify : {json.dumps(fail_result)}'

  def trigger_exist(self, data):
      """

      Args:
          data:

      Returns:

      """

      schema = data.get('schema', 'public')
      trigger_name = data.get('trigger name')
      event_table = data.get('event table')
      event = data.get('event')
      action_orientation = data.get('action orientation')
      action_timing = data.get('action timing')
      execution_statement = data.get('execution statement')

      if trigger_name is None:
          return False, 'trigger name is not defined'
      else:
          trigger_query = f"""SELECT * FROM information_schema.triggers where 
                                          trigger_schema='{schema}' and 
                                          trigger_name='{trigger_name}'; 
                                      """
          data, column = self.pg_db_connector.run_select_query(trigger_query)
          if len(data) > 0:
              function_data = data[0]
              failed = {}
              actual_event_table = function_data[column.index('event_object_table')]
              actual_event = function_data[column.index('event_manipulation')]
              actual_action_orientation = function_data[column.index('action_orientation')]
              actual_action_timing = function_data[column.index('action_timing')]
              actual_execution_statement = function_data[column.index('action_statement')]

              if actual_event_table != event_table:
                  failed['event_table'] = {'actual': actual_event_table,
                                           'expected': event_table}
              if actual_event != event:
                  failed['event'] = {'actual': actual_event,
                                     'expected': event}
              if actual_action_orientation != action_orientation:
                  failed['action_orientation'] = {'actual': actual_action_orientation,
                                                  'expected': action_orientation}
              if actual_action_timing != action_timing:
                  failed['action_timing'] = {'actual': actual_action_timing,
                                             'expected': action_timing}
              if actual_execution_statement != execution_statement:
                  failed['execution_statement'] = {'actual': actual_execution_statement,
                                                   'expected': execution_statement}

              if len(failed) > 0:
                  return False, f'Failed to validate : {failed}'
              else:
                  return True, ''
          else:
              return False, 'Trigger not Found'

  def trigger_not_exist(self, data):
      """

      Args:
          data:

      Returns:

      """

      schema = data.get('schema', 'public')
      trigger_name = data.get('trigger name')

      if trigger_name is None:
          return False, 'trigger name is not defined'
      else:
          trigger_query = f"""SELECT * FROM information_schema.triggers where 
                                          trigger_schema='{schema}' and 
                                          trigger_name='{trigger_name}'; 
                                      """
          data, column = self.pg_db_connector.run_select_query(trigger_query)
          if len(data) == 0:
              return True, 'Trigger not Found'
          else:
              return False, 'Trigger Found'

  def index_exist(self, data):
      """

      Args:
          data:

      Returns:

      """

      schema = data.get('schema', 'public')
      index_name = data.get('index name')
      table_name = data.get('table name')
      column_name = data.get('column name')

      if index_name is None:
          return False, 'index name is not defined'
      elif table_name is None:
          return False, 'table name is not defined'
      elif column_name is None:
          return False, 'column name is not defined'
      else:
          index_query = f"""select
                                      count(*)
                                  from
                                      pg_class t,
                                      pg_class i,
                                      pg_index ix,
                                      pg_attribute a
                                  where
                                      t.oid = ix.indrelid
                                      and i.oid = ix.indexrelid
                                      and a.attrelid = t.oid
                                      and a.attnum = ANY(ix.indkey)
                                      and t.relkind = 'r'
                                      and t.relname = '{table_name}'
                                      and i.relname = '{index_name}' 
                                      and a.attname = '{column_name}' """
          cursor = self.pg_db_connector.db_connection.cursor()
          cursor.execute(index_query)
          data = cursor.fetchall()
          if 1 == data[0][0]:
              return True, ''
          else:
              return False, f'Index [{index_name}] not found'

  def data_change(self, data):
      """

      Args:
          data:
      """
      table_name = data.get('table name')
      column_name = data.get('column name')
      verification = data.get('verification')
      common_column = data.get('common column')

      query = f''' select * from {table_name}'''
      current_data, current_column = self.pg_db_connector.run_select_query(query)
      previous_column, previous_data = '', ''

      try:
          pkl_file = os.path.abspath(Constants.BACKUP_TABLES + f'/{table_name}.pkl')
          with open(pkl_file, 'rb') as pkl_file_descriptor:
              previous_column = pickle.load(pkl_file_descriptor)
              _ = pickle.load(pkl_file_descriptor)
              previous_data = pickle.load(pkl_file_descriptor)
      except Exception as Err:
          raise Exception(f'Previous database data for table {table_name} not found, Err : {str(Err)}')

      df_current = pandas.DataFrame(current_data, columns=current_column)
      df_previous = pandas.DataFrame(previous_data, columns=previous_column)
      fail_result = []
      for common_value in df_current[common_column]:
          curr_row = df_current[df_current[common_column] == common_value]
          prev_row = df_previous[df_previous[common_column] == common_value]

          expected = list(prev_row[column_name])[0]
          actual = list(curr_row[column_name])[0]

          if verification == 'not equal':
              if actual == expected:
                  fail_result.append({'Verification': verification,
                                      'Expected': expected, 'Actual': actual
                                      })
          if verification == 'equal':
              if actual != expected:
                  fail_result.append({'Verification': verification,
                                      'Expected': expected, 'Actual': actual
                                      })

      if len(fail_result) > 0:
          return False, f'Failed to validate : {fail_result}'
      return True, ''

  def not_verify(self, data):
      """

      Args:
          data:

      Returns:

      """
      reason = data.get('reason')

      if reason is None:
          return False, 'reason is not defined'

      return True, 'DoNotVerify'

  @staticmethod
  def list_schema_version_to_verify(from_schema, to_schema):
      """
      list and return yaml files to verify
      Returns:
      """
      from_schema = version.parse(from_schema)
      to_schema = version.parse(to_schema)
      sql_list = []
      sorted_version = sorted(Constants.VERSIONS.values(), key=lambda x: version.parse(x))
      if from_schema.base_version in sorted_version and to_schema.base_version in sorted_version:
          from_index = sorted_version.index(from_schema.base_version)
          to_index = sorted_version.index(to_schema.base_version)

          if from_schema < to_schema:
              version_filter = sorted_version[from_index:to_index + 1]
          else:
              version_filter = sorted_version[from_index:to_index - 1:-1]

          for index, value in enumerate(version_filter):
              if len(version_filter) - 1 == index:
                  break
              sql_list.append(f'{value}%{version_filter[index + 1]}.yaml')
          return sql_list
      return []

  def verify_database(self, from_schema, to_schema):
      """
      this function will verify database
      Args:
          from_schema : the old db schema
          to_schema : the new db schema

      """
      test_case = TestCaseHelper("validate")
      print(f'[DataHelper] > Verifying Schema Versions')
      print(f'[DataHelper] > Fetching Schema details')
      current_db_version = test_case.get_database_columns_value(table_name='schema_versions',
                                                                columns_name='db_version')
      current_db_version_id = current_db_version['db_version']
      print(f'[DataHelper] > Current Database Version : [{current_db_version_id}] ')
      current_pfmodel_version = test_case.get_database_columns_value(table_name='schema_versions',
                                                                     columns_name='pfmodel_version')
      current_pfmodel_version_id = current_pfmodel_version['pfmodel_version']
      print(f'[DataHelper] > Current PF Model version : [{current_pfmodel_version_id}]')
      print(f'[DataHelper] > Selected Schema  version : [{to_schema}]')
      db_version = str(current_db_version_id)
      select_schema = str(to_schema)
      if db_version != select_schema:
          print(
              f'[DataHelper] > Schema versions NOT MATCHED -> [ current schema version: {current_db_version_id} & selected schema version: {select_schema}]')
      else:
          print(
              f'[DataHelper] > Schema versions MATCHED -> [ current schema version: {current_db_version_id} & selected schema version: {select_schema}]')

      print(f'[DataHelper] > Fetching schema version details')
      sql_files = self.list_schema_version_to_verify(from_schema, to_schema)
      if len(sql_files) < 1:
          return None, 'Database Version not found in constants'
      print(f'[DataHelper] > Schema version scripts found : {len(sql_files)}')
      final_result = {}
      filter_function = {
          '@table[not exist]': self.table_not_exist,
          '@table[exist]': self.table_exist,
          '@table[properties]': self.table_properties,

          '@column[exist]': self.column_exist,
          '@column[not exist]': self.column_not_exist,
          '@column[value]': self.column_value,
          '@column[properties]': self.column_properties,
          '@column[update from table]': self.column_update_from_table,
          '@column[multiple value]': self.column_value_multiple,

          '@row[exist]': self.row_value_multiple,
          '@row[not exist]': self.row_value_multiple_delete,

          '@sequence[not exist]': self.sequence_not_exist,
          '@sequence[exist]': self.sequence_exist,
          '@sequence[current value]': self.sequence_current_value,
          '@sequence[owner]': self.sequence_owner,

          '@constraint[not exist]': self.constraint_not_exist,
          '@constraint[exist]': self.constraint_exist,
          '@constraint[foreign key]': self.constraint_foreign_key,

          '@function[exist]': self.function_exists,
          '@function[not exist]': self.function_not_exists,
          '@function[properties]': self.function_properties,

          '@trigger[exist]': self.trigger_exist,
          '@trigger[not exist]': self.trigger_not_exist,

          '@index[exist]': self.index_exist,
          '@data[pkl]': self.data_change,

          '@verify[not verify]': self.not_verify,
      }
      self.pg_db_connector = DBConnector(database_name='farming')
      self.pg_db_connector.get_connection()
      final_result_item = 0
      for sql_file in sql_files:
          print('\n' + f'  Verifying sql file : [{sql_file}]  '.center(125, '%') + '\n')
          yaml_file = os.path.abspath(Constants.YAML_FILES + f'/{sql_file.replace("sql", "yaml")}')
          data = yaml.load(open(yaml_file, 'r'), Loader=yaml.FullLoader)
          for item, query_data in data.items():
              query = query_data.get('query')
              verify = query_data.get('verify')
              final_result_item += 1
              final_result[final_result_item] = {'query': query, 'verify': {}, 'query result': 'NA',
                                                 'sql script': sql_file, 'script item': item}
              print(f'[DataHelper] > Script : [{sql_file}]')
              print(f'[DataHelper] > YAML : [{sql_file.replace("sql", "yaml")}]')
              print(f'[DataHelper] > Total Item No : [{final_result_item}]')
              print(f'[DataHelper] > Script Item No : [{item}]')
              query = query.replace("\n", "\n\t\t\t\t\t\t")
              print(f'[DataHelper] > Query : [{query}]')

              if verify is not None:
                  step_results = []
                  is_do_not_verify = False
                  for step, verification_item in enumerate(verify):
                      print(''.center(100, '_'))
                      print(f'[DataHelper] > Verification Step : [{step}]')
                      step_result = False
                      exception_str = ''
                      function_name = None
                      for function_name, function_data in verification_item.items():
                          is_do_not_verify = False
                          try:
                              function_evaluate = filter_function.get(function_name)
                              if function_evaluate is not None:
                                  print(f'[DataHelper] > Function verify : {function_name}')
                                  print(f'[DataHelper] > Function data : {function_data}')
                                  step_result, exception_str = function_evaluate(function_data)
                                  if exception_str == 'DoNotVerify':
                                      is_do_not_verify = True
                                  final_result[final_result_item]['verify'][step] = {'function': function_name,
                                                                                     'data': function_data,
                                                                                     'step result': step_result,
                                                                                     'Exception': exception_str}
                              else:
                                  exception_str = f'function not found : [{function_name}]'
                                  final_result[final_result_item]['verify'][step] = {'function': function_name,
                                                                                     'data': function_data,
                                                                                     'step result': step_result,
                                                                                     'Exception': exception_str}

                          except Exception as Err:
                              exception_str = str(Err)
                              final_result[final_result_item]['verify'][step] = {'function': function_name,
                                                                                 'data': function_data,
                                                                                 'step result': step_result,
                                                                                 'Exception': traceback.format_exc()}
                      print(f'[DataHelper] > Function verify : {function_name}, Status : [{step_result}]')
                      step_results.append(step_result)
                      if not step_result:
                          print(f'[DataHelper] > Exception : {exception_str}')
                      print(''.center(100, '_'))

                  if is_do_not_verify:
                      final_result[final_result_item]['query result'] = 'DoNotVerify'
                  elif len(step_results) == 0:
                      final_result[final_result_item]['query result'] = 'NA'
                  elif all(step_results):
                      final_result[final_result_item]['query result'] = 'PASS'
                  else:
                      final_result[final_result_item]['query result'] = 'FAIL'
                  print(f'[DataHelper] > Query Status : [{final_result[final_result_item]["query result"]}]')
              print('\n' + ''.center(100, '*') + '\n')

          print(f'[DataHelper] > SQL file verified [{sql_file}]')
      self.pg_db_connector.close_connection()
      return final_result, None

  @staticmethod
  def store_json_data_file(file_path, data):
      """

      Args:
          file_path:
          data:
      """
      print(f'[DataHelper] > Storing json data into file')
      with open(file_path, 'w+', encoding='utf8') as json_file:
          json.dump(data, json_file, sort_keys=True, indent=2)

  @staticmethod
  def create_excel_report(json_path, report_path):
      """

      Args:
          json_path:
          report_path:
      """
      print(f'[DataHelper] > Creating Excel Report')
      final_data = []
      with open(json_path, 'r', encoding='utf8') as json_file:
          report_data = json.load(json_file)
          for item, query_result_data in report_data.items():
              exception_data = ''
              for step_id, step_data in query_result_data.get('verify').items():
                  if not step_data['step result']:
                      exception_data += f'---------------------------' \
                                        f'\nStep Id : {step_id} ,\nFunction Name: {step_data["function"]}\n' \
                                        f'Exception :{step_data["Exception"]}'
              temp = {'SQL Script': query_result_data.get('sql script').replace('yaml', 'sql'),
                      'Query Item': query_result_data.get('script item'),
                      'Query': query_result_data.get('query'),
                      'Query Result': query_result_data.get('query result'),
                      'Exception Details': exception_data}
              final_data.append(temp)
      print(f'[DataHelper] > Data Found [{len(final_data)}]')
      dataframe = pandas.DataFrame(final_data)
      dataframe.to_excel(report_path, sheet_name="Data Persistent Dashboard")
      print(f'[DataHelper] > Report Stored at : {report_path}')

  def create_html_report(self, json_path, report_path):
      """

      Args:
          json_path:
          report_path:
      """
      print(f'[DataHelper] > Creating Html Report')
      final_data = {}
      with open(json_path, 'r', encoding='utf8') as json_file:
          report_data = json.load(json_file)
          for item, query_result_data in report_data.items():
              yaml_script = query_result_data.get('sql script', '').replace('.sql', '').strip()
              query = query_result_data.get('query')
              query_result = query_result_data.get('query result')
              script_item = query_result_data.get('script item')
              verify = query_result_data.get('verify')
              temp = {'query': query, 'query result': query_result, 'script item': script_item, 'verify': verify}
              if yaml_script in final_data:
                  final_data[yaml_script]['yaml data'].append(temp)

              else:
                  final_data[yaml_script] = {'yaml data': [temp]}

              if 'yaml result' in final_data[yaml_script].keys():
                  if 'PASS' in final_data[yaml_script]['yaml result'] and query_result == 'FAIL':
                      final_data[yaml_script]['yaml result'] = 'FAIL'
              else:
                  final_data[yaml_script]['yaml result'] = 'PASS'

      print(f'[DataHelper] > Successfully filter out results')
      print(f'[DataHelper] > Generating scaffolding for html report')

      # Starting Html
      formatted_html_str = '''
          <!DOCTYPE html>
          <html lang="en">
          <head>
              <meta charset="UTF-8">
              <title> Data Persistent - Report </title>
              <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/css/bootstrap.min.css">
              <link href="https://netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap-glyphicons.css" rel="stylesheet">
              <link href="https://maxcdn.bootstrapcdn.com/font-awesome/4.2.0/css/font-awesome.min.css" rel="stylesheet">
          </head>
          <body style="background-color:black;">
          <div class="container">
              <div class="row">
                  <div class="col-sm-12">
                      <div class="jumbotron">
                          <center><h1 class="display-4">Data Persistent Report</h1></center>
                      </div>
                  </div>
          
              </div>
              <br><br>
          <div class="accordion md-accordion accordion-blocks" id="main_accordion" role="tablist"
           aria-multiselectable="true">
  
          '''
      for yaml_script, yaml_data in final_data.items():
          print(f'[DataHelper] > Creating Scaffold for script {yaml_script} ')
          result = yaml_data.get('yaml result')
          yaml_data = yaml_data.get('yaml data')
          yaml_script_id = yaml_script.replace('.', '').replace('%', '').replace('yaml', '')
          card_color_yaml = 'bg-danger'
          if result == 'PASS':
              card_color_yaml = 'bg-success'

          # yaml_item
          formatted_html_str += f'''
              <div class="card">
              <div class="card-header {card_color_yaml}" role="tab" id="header{yaml_script_id}">
                  <a data-toggle="collapse" data-parent="#main_accordion" href="#collapse{yaml_script_id}" aria-expanded="true"
                     aria-controls="collapse{yaml_script_id}">
                      <h4 class="mt-1 mb-0">
                          <span class="font-weight-bold" style="padding:10px;color:black">
                              {yaml_script.replace('.yaml', '').replace('%', ' - ')}
                          </span>
                      </h4>
                  </a>
  
              </div>
              <div id="collapse{yaml_script_id}" class="collapse" role="tabpanel" aria-labelledby="header{yaml_script_id}"
                   data-parent="#main_accordion">
                  <div class="card-body">
              
              '''
          formatted_html_str += self.get_query_items(yaml_script_id, yaml_data)
          formatted_html_str += '</div></div></div>'
          print(f'[DataHelper] > Finished Scaffold for script {yaml_script} ')
      # Ending html
      formatted_html_str += '''
          </div>
          <script src="https://code.jquery.com/jquery-3.6.0.min.js" integrity="sha256-/xUj+3OJU5yExlq6GSYGSHk7tPXikynS7ogEvDej/m4=" crossorigin="anonymous"></script>
          <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.6.0/dist/js/bootstrap.bundle.min.js"></script>
          <script>
          function toggleIcon(e) {
              $(e.target)
                  .prev('.panel-heading')
                  .find(".more-less")
                  .toggleClass('glyphicon-plus glyphicon-minus');
          }
          $('.panel-group').on('hidden.bs.collapse', toggleIcon);
          $('.panel-group').on('shown.bs.collapse', toggleIcon);
          </script>
          </div>
          </body>
          </html>
          '''

      with open(report_path, 'w+') as html_file:
          html_file.write(formatted_html_str)
      print(f'[DataHelper] > Created Html Report')

  @staticmethod
  def get_query_items(yaml_script_id, yaml_data):
      """
      Create query items
      Args:
          yaml_script_id:
          yaml_data:

      Returns:

      """
      formatted_html_str = f''
      for item_data in yaml_data:
          query_str = item_data.get('query')
          query_result = item_data.get('query result')
          query_item = item_data.get('script item')
          steps_data = item_data.get('verify')
          table_color_yaml = 'table-danger'
          card_color_yaml = 'bg-danger'
          if query_result == 'PASS':
              card_color_yaml = 'bg-success'
              table_color_yaml = 'table-success'
          if query_result == 'NA':
              card_color_yaml = 'bg-warning'
          if query_result == 'DoNotVerify':
              table_color_yaml = 'table-secondary'
              card_color_yaml = 'bg-secondary'

          formatted_html_str += f'''
              <div class="accordion" id="accordion{yaml_script_id}query">
              <div class="card z-depth-0 bordered ">
                  <div class="card-header {card_color_yaml}" id="heading{query_item}">
                      <button class="btn btn-link" type="button" data-toggle="collapse"
                              data-target="#collapse{query_item}"
                              aria-expanded="true" aria-controls="collapse{query_item}" style="padding:10px;color:black">
                          <h5 class="mb-0 font-weight-bold"> Query Item #{query_item}</h5>
                      </button>
                  </div>
                  <div id="collapse{query_item}" class="collapse" aria-labelledby="heading{query_item}"
                       data-parent="#accordion{yaml_script_id}query">
                      <div class="card-body">
                          <table class="table {table_color_yaml}">
                              <thead>
                              <tr>
                                  <th>Field</th>
                                  <th>Info</th>
                              </tr>
                              </thead>
                              <tbody>
                              <tr>
                                  <td>Query</td>
                                  <td>{query_str}
                                  </td>
                              </tr>
                              <tr>
                                  <td>Query result</td>
                                  <td>{query_result}</td>
                              </tr>
                              <tr>
                                  <td>Script item</td>
                                  <td>{query_item}</td>
                              </tr>
                              </tbody>
                          </table>
              '''

          for step_no, step_data in steps_data.items():
              step_no = int(step_no) + 1
              btn_color = 'btn-success'
              table_color = 'table-success'
              function = step_data.get('function')
              step_result = step_data.get('step result')
              exception_str = step_data.get('Exception')
              data = str(step_data.get('data'))
              if not step_result:
                  btn_color = 'btn-danger'
                  table_color = 'table-danger'

              formatted_html_str += f'''
                  <button data-toggle="collapse" data-target="#steps{yaml_script_id}item{query_item}step{step_no}"
                  class="{btn_color}"
                  style="height:40px;width:80px;">Step - {step_no}
                  </button>
                  <div id="steps{yaml_script_id}item{query_item}step{step_no}" class="collapse"><br><br>
                  <table class="table {table_color}">
                      <thead>
                          <tr>
                              <th>Field</th>
                              <th>Info</th>
                          </tr>
                          </thead>
                          <tbody>
                          <tr>
                              <td>Step No</td>
                              <td>{step_no}</td>
                          </tr>
                          <tr>
                              <td>Function</td>
                              <td>{function}</td>
                          </tr>
                          <tr>
                              <td>Step result</td>
                              <td>{step_result}</td>
                          </tr>
                          <tr>
                              <td>Data</td>
                              <td>{data}
                              </td>
                          </tr>
                          <tr>
                              <td>Exception</td>
                              <td>{exception_str}
                              </td>
                          </tr>
                              </tbody>
                          </table>
                      </div>
                  '''

          formatted_html_str += '''
              </div>
              </div>
              </div>
              </div>'''

      return formatted_html_str
