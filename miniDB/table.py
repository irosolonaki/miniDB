from __future__ import annotations
from tabulate import tabulate
import pickle
import os
import sys

sys.path.append(f'{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}/miniDB')

from misc import get_op, split_condition


class Table:
    '''
    Table object represents a table inside a database

    A Table object can be created either by assigning:
        - a table name (string)
        - column names (list of strings)
        - column types (list of functions like str/int etc)
        - primary (name of the primary key column)

    OR

        - by assigning a value to the variable called load. This value can be:
            - a path to a Table file saved using the save function
            - a dictionary that includes the appropriate info (all the attributes in __init__)

    '''
    def __init__(self, name=None, column_names=None, column_types=None, primary_key=None, load=None,columns_unique=None): # added unique constraint

        if load is not None:
            # if load is a dict, replace the object dict with it (replaces the object with the specified one)
            if isinstance(load, dict):
                self.__dict__.update(load)
                # self._update()
            # if load is str, load from a file
            elif isinstance(load, str):
                self._load_from_file(load)

        # if name, columns_names and column types are not none
        elif (name is not None) and (column_names is not None) and (column_types is not None):

            self._name = name

            if len(column_names)!=len(column_types):
                raise ValueError('Need same number of column names and types.')

            self.column_names = column_names

            self.columns = []

            for col in self.column_names:
                if col not in self.__dir__():
                    # this is used in order to be able to call a column using its name as an attribute.
                    # example: instead of table.columns['column_name'], we do table.column_name
                    setattr(self, col, [])
                    self.columns.append([])
                else:
                    raise Exception(f'"{col}" attribute already exists in "{self.__class__.__name__} "class.')

            self.column_types = [eval(ct) if not isinstance(ct, type) else ct for ct in column_types]
            self.data = [] # data is a list of lists, a list of rows that is.

            self.columns_unique = columns_unique if columns_unique is not None else [] # instance for unique constraint
            #self.unique_idx = [self.column_names.index(i) for i in columns_unique] if columns_unique is not None else []
            #print("unique columns: ", columns_unique)

            '''
            for col_un in columns_unique:
                if columns_unique[col_un] is not None:
                    self.unique_idx = self.column_names.index(columns_unique[col_un]) #!!!!
                else:
                    self.unique_idx = None
            '''

            if columns_unique is not None:
                self.unique_idx=[]
                for u in columns_unique:
                    self.unique_idx.append(self.column_names.index(u))
            else:
                self.unique_idx = None

            #self.columns_unique = columns_unique

            # if primary key is set, keep its index as an attribute
            if primary_key is not None:
                self.pk_idx = self.column_names.index(primary_key)
            else:
                self.pk_idx = None

            self.pk = primary_key
            # self._update()

    # if any of the name, columns_names and column types are none. return an empty table object

    def column_by_name(self, column_name):
        return [row[self.column_names.index(column_name)] for row in self.data]


    def _update(self):
        '''
        Update all the available columns with the appended rows.
        '''
        self.columns = [[row[i] for row in self.data] for i in range(len(self.column_names))]
        for ind, col in enumerate(self.column_names):
            setattr(self, col, self.columns[ind])

    def _cast_column(self, column_name, cast_type):
        '''
        Cast all values of a column using a specified type.

        Args:
            column_name: string. The column that will be casted.
            cast_type: type. Cast type (do not encapsulate in quotes).
        '''
        # get the column from its name
        column_idx = self.column_names.index(column_name)
        # for every column's value in each row, replace it with itself but casted as the specified type
        for i in range(len(self.data)):
            self.data[i][column_idx] = cast_type(self.data[i][column_idx])
        # change the type of the column
        self.column_types[column_idx] = cast_type
        # self._update()


    def _insert(self, row, insert_stack=[]):
        '''
        Insert row to table.

        Args:
            row: list. A list of values to be inserted (will be casted to a predifined type automatically).
            insert_stack: list. The insert stack (empty by default).
        '''
        if len(row)!=len(self.column_names):
            raise ValueError(f'ERROR -> Cannot insert {len(row)} values. Only {len(self.column_names)} columns exist')

        for i in range(len(row)):
            # for each value, cast and replace it in row.
            try:
                row[i] = self.column_types[i](row[i])
            except ValueError:
                if row[i] != 'NULL':
                    raise ValueError(f'ERROR -> Value {row[i]} of type {type(row[i])} is not of type {self.column_types[i]}.')
            except TypeError as exc:
                if row[i] != None:
                    print(exc)
            
            
            if (self.column_names[i] in self.columns_unique and str(row[i]) in [str(val) for val in self.column_by_name(self.column_names[i])]):
                print(f'## ERROR: Cannot insert duplicate value "{str(row[i])}" in column "{self.column_names[i]}". It has the unique constraint.')
                raise ValueError(f'## ERROR: Cannot insert duplicate value "{str(row[i])}" in column "{self.column_names[i]}". It has the unique constraint.')
                

            #row[i] = self.column_types[i](row[i])
            
            # if value is to be appended to the primary_key column, check that it doesnt alrady exist (no duplicate primary keys)
            if i==self.pk_idx and row[i] in self.column_by_name(self.pk):
                raise ValueError(f'## ERROR -> Value {row[i]} already exists in primary key column.')
            elif i==self.pk_idx and row[i] is None:
                raise ValueError(f'## ERROR -> The value of the primary key cannot be None.')

        # if insert_stack is not empty, append to its last index
        if insert_stack != []:
            self.data[insert_stack[-1]] = row
        else: # else append to the end
            self.data.append(row)
        # self._update()

    def _update_rows(self, set_value, set_column, condition):
        '''
        Update where Condition is met.

        Args:
            set_value: string. The provided set value.
            set_column: string. The column to be altered.
            condition: string. A condition using the following format:
                'column[<,<=,=,>=,>]value' or
                'value[<,<=,=,>=,>]column'.
                
                Operatores supported: (<,<=,=,>=,>)
        '''
        # parse the condition
        #column_name, operator, value = self._parse_condition(condition)

        # get the condition and the set column
        #column = self.column_by_name(column_name)
        set_column_idx = self.column_names.index(set_column)

        #set_columns_indx = [self.column_names.index(set_column_name) for set_column_name in set_column_names]

        if 'not ' in condition and ' between ' not in condition:
                condition = condition.replace('not ', '')
               # condition_columnn, op, value = split_condition(condition,True)
                #print(condition_column)
                #print(condition)
                column_name, operator, value = self._parse_condition(condition, False, True)
                column = self.column_by_name(column_name)
                rows = [ind for ind, x in enumerate(column) if get_op(operator, x, value)]
                for row_ind, column_value in enumerate(column):
                    if get_op(operator, column_value, value):
                        self.data[row_ind][set_column_idx] = set_value

        elif ' between ' and ' and ' in condition:
                if 'not ' in condition:
                    condition = condition.replace('not ', '') 
                    notcheck = True
                else:
                    notcheck = False

                splt = condition.split(' between ', 1) # split condition one time on between keyword

                # if splt is more than 1 characters, split "splt" one time on the 'and' keyword
                if len(splt)>1:
                    if len(splt[1])>1:

                        # column name, between ... and ...
                        # splt[0], 'between', splt[1]
                        splt_and = splt[1].split(' and ', 1)
                        #value1 and value2
                        #splt_and[0], 'and', splt_and[1]

                        #remove whitespace
                        condition_column = splt[0].replace(' ', '') # name of column
                        value1 = splt_and[0].replace(' ', '') # name of the first value
                        value2 = splt_and[1].replace(' ', '') # name of second value
                
                column = self.column_by_name(condition_column) # get column as a list
                column_to_str = [str(x) for x in column] # make column list of strings

                values = []
                
                if notcheck: # we reverse the operators in case there is the 'not' keyword in front of the 'between' keyowrd
                    # not between 67000 and 75000 => value < 67000 or value > 75000
                    if value1.isdigit() and value2.isdigit(): #if values are numbers
                        values = [x for x in column_to_str if(x!='None' and int(x) < int(value1) or int(x) > int(value2))] # exclude None in case of deleted record
                    else: # else if we compare strings, it kinda works if we check: name between a and k
                        values = [x for x in column_to_str if(x < value1 or x > value2)]
                else: # normal between format
                    # between 67000 and 75000 => value >= 67000 and value <= 75000
                    if value1.isdigit() and value2.isdigit():
                        values = [x for x in column_to_str if(x!='None' and int(x) >= int(value1) and int(x) <= int(value2))]
                    else:
                        values = [x for x in column_to_str if(x >= value1 and x <= value2)] 
                
                set_column_idx = self.column_names.index(set_column)

                column = self.column_by_name(column_name)
                for row_ind, column_value in enumerate(column_to_str):
                    for i in range(len(values)):
                        if (column_value == values[i]):
                            self.data[row_ind][set_column_idx] = set_value
        
        else:
            # parse the condition
            column_name, operator, value = self._parse_condition(condition)

            # get the condition and the set column
            column = self.column_by_name(column_name)
            set_column_idx = self.column_names.index(set_column)

            # for each value in column, if condition, replace it with set_value
            for row_ind, column_value in enumerate(column):
                if get_op(operator, column_value, value):
                    self.data[row_ind][set_column_idx] = set_value

        # self._update()
                # print(f"Updated {len(indexes_to_del)} rows")


    def _delete_where(self, condition):
        '''
        Deletes rows where condition is met.

        Important: delete replaces the rows to be deleted with rows filled with Nones.
        These rows are then appended to the insert_stack.

        Args:
            condition: string. A condition using the following format:
                'column[<,<=,==,>=,>]value' or
                'value[<,<=,==,>=,>]column'.
                
                Operatores supported: (<,<=,==,>=,>)
        '''
        #column_name, operator, value = self._parse_condition(condition)
        
        indexes_to_del = []

        if 'not ' in condition and ' between ' not in condition:
                condition = condition.replace('not ', '')
               # condition_columnn, op, value = split_condition(condition,True)
                #print(condition_column)
                #print(condition)
                column_name, operator, value = self._parse_condition(condition, False, True)
                column = self.column_by_name(column_name)
                rows = [ind for ind, x in enumerate(column) if get_op(operator, x, value)]
                for index, row_value in enumerate(column):
                    if get_op(operator, row_value, value):
                        indexes_to_del.append(index)

        elif ' between ' and ' and ' in condition:
                if 'not ' in condition:
                    condition = condition.replace('not ', '') 
                    notcheck = True
                else:
                    notcheck = False

                splt = condition.split(' between ', 1) # split condition one time on between keyword

                # if splt is more than 1 characters, split "splt" one time on the 'and' keyword
                if len(splt)>1:
                    if len(splt[1])>1:

                        # column name, between ... and ...
                        # splt[0], 'between', splt[1]
                        splt_and = splt[1].split(' and ', 1)
                        #value1 and value2
                        #splt_and[0], 'and', splt_and[1]

                        #remove whitespace
                        condition_column = splt[0].replace(' ', '') # name of column
                        value1 = splt_and[0].replace(' ', '') # name of the first value
                        value2 = splt_and[1].replace(' ', '') # name of second value
                
                column = self.column_by_name(condition_column) # get column as a list
                column_to_str = [str(x) for x in column] # make column list of strings

                values = []
                
                if notcheck: # we reverse the operators in case there is the 'not' keyword in front of the 'between' keyowrd
                    # not between 67000 and 75000 => value < 67000 or value > 75000
                    if value1.isdigit() and value2.isdigit(): #if values are numbers
                        values = [x for x in column_to_str if(x!='None' and int(x) < int(value1) or int(x) > int(value2))] # exclude None in case of deleted record
                    else: # else if we compare strings, it kinda works if we check: name between a and k
                        values = [x for x in column_to_str if(x < value1 or x > value2)]
                else: # normal between format
                    # between 67000 and 75000 => value >= 67000 and value <= 75000
                    if value1.isdigit() and value2.isdigit():
                        values = [x for x in column_to_str if(x!='None' and int(x) >= int(value1) and int(x) <= int(value2))]
                    else:
                        values = [x for x in column_to_str if(x >= value1 and x <= value2)] 

                column = self.column_by_name(column_name)
                for index, row_value in enumerate(column):
                    for i in range(len(values)):
                        if row_value == values[i]:
                            indexes_to_del.append(index)
                            #print("with special word: ", indexes_to_del)
        
        else:
            column_name, operator, value = self._parse_condition(condition)
            column = self.column_by_name(column_name)
            for index, row_value in enumerate(column):
                if get_op(operator, row_value, value):
                    indexes_to_del.append(index)
                    #print("without special word: ", indexes_to_del)

        # we pop from highest to lowest index in order to avoid removing the wrong item
        # since we dont delete, we dont have to to pop in that order, but since delete is used
        # to delete from meta tables too, we still implement it.

        for index in sorted(indexes_to_del, reverse=True):
            
            if self._name[:4] != 'meta':
                # if the table is not a metatable, replace the row with a row of nones
                self.data[index] = [None for _ in range(len(self.column_names))]
            else:
                self.data.pop(index)

        # self._update()
        # we have to return the deleted indexes, since they will be appended to the insert_stack
        return indexes_to_del


    def _select_where(self, return_columns, condition=None, distinct=False, order_by=None, desc=True, limit=None):
        '''
        Select and return a table containing specified columns and rows where condition is met.

        Args:
            return_columns: list. The columns to be returned.
            condition: string. A condition using the following format:
                'column[<,<=,==,>=,>]value' or
                'value[<,<=,==,>=,>]column'.
                
                Operatores supported: (<,<=,==,>=,>,not,between)
            distinct: boolean. If True, the resulting table will contain only unique rows (False by default).
            order_by: string. A column name that signals that the resulting table should be ordered based on it (no order if None).
            desc: boolean. If True, order_by will return results in descending order (False by default).
            limit: int. An integer that defines the number of rows that will be returned (all rows if None).
        '''
        #multiple = False        
        # if * return all columns, else find the column indexes for the columns specified
        if return_columns == '*':
            return_cols = [i for i in range(len(self.column_names))]
        else:
            return_cols = [self.column_names.index(col.strip()) for col in return_columns.split(',')]

        #print("return_cols:", return_cols)
        #print(condition)
        # if condition is None, return all rows
        # if not, return the rows with values where condition is met for value
        if condition is not None:
            notcheck = False
            if 'not ' in condition and ' between ' not in condition: 
                condition = condition.replace('not ', '') # split condition one time on 'not' keyword
                #print(condition)
                column_name, operator, value = self._parse_condition(condition, False, True) # thrid parameter is about 'notcheck', a variable set to true if 'not' exists in said condition
                column = self.column_by_name(column_name)
                rows = [ind for ind, x in enumerate(column) if get_op(operator, x, value)]

            elif ' between ' in condition and ' and ' in condition:
                if 'not ' in condition:
                    condition = condition.replace('not ', '') # remove not from the condition
                    notcheck = True # used to negate the operators
                else:
                    notcheck = False

                splt = condition.split(' between ', 1) # split condition one time on between keyword

                # if splt is more than 1 characters, split "splt" one time on the 'and' keyword
                if len(splt)>1:
                    if len(splt[1])>1:

                        # column name, between ... and ...
                        # splt[0], 'between', splt[1]
                        splt_and = splt[1].split(' and ', 1)
                        #value1 and value2
                        #splt_and[0], 'and', splt_and[1]

                        #remove whitespace
                        condition_column = splt[0].replace(' ', '') # name of column
                        value1 = splt_and[0].replace(' ', '') # name of the first value
                        value2 = splt_and[1].replace(' ', '') # name of second value
                
                column = self.column_by_name(condition_column) # get column as a list
                column_to_str = [str(x) for x in column] # make column list of strings

                values = []

                if notcheck: # we reverse the operators in case there is the 'not' keyword in front of the 'between' keyowrd
                    # not between 67000 and 75000 => value < 67000 or value > 75000
                    if value1.isdigit() and value2.isdigit(): #if values are numbers
                        values = [x for x in column_to_str if(x!='None' and int(x) < int(value1) or int(x) > int(value2))] # exclude None in case of deleted record
                    else: # else if we compare strings, it kinda works if we check: name between a and k
                        values = [x for x in column_to_str if(x < value1 or x > value2)]
                else: # normal between format
                    # between 67000 and 75000 => value >= 67000 and value <= 75000
                    if value1.isdigit() and value2.isdigit():
                        values = [x for x in column_to_str if(x!='None' and int(x) >= int(value1) and int(x) <= int(value2))]
                    else:
                        values = [x for x in column_to_str if(x >= value1 and x <= value2)] 
                

                rows = [ind for ind, x in enumerate(column_to_str) if(x in list(values))]
            elif ' and ' in condition:
                list_conditions = [] # create a list for all the conditions
                list_rows = [] # list containing the rows that correspond with the conditon
                rows = []           
                splt = condition.split(' and ') # split the condition in the 'and' keyword

                for i in range(len(splt)):
                    list_conditions.append(splt[i]) # add the condition to the list
                
                for i in range(len(list_conditions)): # for each condition in the list with the conditions
                    column_name, operator, value = self._parse_condition(list_conditions[i]) # parse the condition as usual
                    column = self.column_by_name(column_name)
                    list_rows.append([ind for ind, x in enumerate(column) if get_op(operator, x, value)]) # add them to the list of total rows
                                 
                rows = set(list_rows[0]).intersection(*list_rows) # create an intersection to get the records that match all the conditions              
                
            elif ' or ' in condition:
                list_conditions = [] # create a list for all the conditions
                list_rows = [] # list containing the rows that correspond with the conditon
                rows = []              
                splt = condition.split(' or ') # split the condition in the 'or' keyword
                for i in range(len(splt)):
                    list_conditions.append(splt[i]) # add the condition to the list

                for i in range(len(list_conditions)): # for each condition in the list with the conditions
                    column_name, operator, value = self._parse_condition(list_conditions[i]) # parse the condition as usual
                    column = self.column_by_name(column_name)
                    list_rows.append([ind for ind, x in enumerate(column) if get_op(operator, x, value)]) # add them to the list of total rows

                for li in list_rows: # for each index in the list of rows
                    for row in li: # and for each row of that index
                        if not row in rows: 
                            rows.append(row) 

            else:
                column_name, operator, value = self._parse_condition(condition)
                column = self.column_by_name(column_name)
                
                rows = [ind for ind, x in enumerate(column) if get_op(operator, x, value)]
                
        
        else:
            rows = [i for i in range(len(self.data))]
            

        # copy the old dict, but only the rows and columns of data with index in rows/columns (the indexes that we want returned)
        
        dict = {(key):([[self.data[i][j] for j in return_cols] for i in rows] if key=="data" else value) for key,value in self.__dict__.items()}
        #print(rows)
        # we need to set the new column names/types and no of columns, since we might
        # only return some columns
        dict['column_names'] = [self.column_names[i] for i in return_cols]
        dict['column_types']   = [self.column_types[i] for i in return_cols]

        s_table = Table(load=dict)

        s_table.data = list(set(map(lambda x: tuple(x), s_table.data))) if distinct else s_table.data

        if order_by:
            s_table.order_by(order_by, desc)

        # if isinstance(limit, str):
        #     try:
        #         k = int(limit)
        #     except ValueError:
        #         raise Exception("The value following 'top' in the query should be a number.")
            
        #     # Remove from the table's data all the None-filled rows, as they are not shown by default
        #     # Then, show the first k rows 
        #     s_table.data.remove(len(s_table.column_names) * [None])
        #     s_table.data = s_table.data[:k]
        if isinstance(limit,str):
            s_table.data = [row for row in s_table.data if any(row)][:int(limit)]

        return s_table


    def _select_where_with_btree(self, return_columns, bt, condition,  distinct=False, order_by=None, desc=True, limit=None):

        # if * return all columns, else find the column indexes for the columns specified
        if return_columns == '*':
            return_cols = [i for i in range(len(self.column_names))]
        else:
            return_cols = [self.column_names.index(colname) for colname in return_columns]

        #print(condition)
        column_name, operator, value = self._parse_condition(condition)
        '''

        # if the column in condition is not a primary key, abort the select
        if column_name != self.column_names[self.pk_idx]:
            print('Column is not PK. Aborting')
        '''

        # here we run the same select twice, sequentially and using the btree.
        # we then check the results match and compare performance (number of operation)
        column = self.column_by_name(column_name)

        # sequential
        rows1 = []
        opsseq = 0
        for ind, x in enumerate(column):
            opsseq+=1
            
            if get_op(operator, x, value):
                rows1.append(ind)
                

        # btree find
        
        rows = bt.find(operator, value)
        

        try:
            k = int(limit)
        except TypeError:
            k = None
        # same as simple select from now on
        rows = rows[:k]
        
        # TODO: this needs to be dumbed down
        dict = {(key):([[self.data[i][j] for j in return_cols] for i in rows] if key=="data" else value) for key,value in self.__dict__.items()}
        
        dict['column_names'] = [self.column_names[i] for i in return_cols]
        dict['column_types']   = [self.column_types[i] for i in return_cols]

        s_table = Table(load=dict)

        s_table.data = list(set(map(lambda x: tuple(x), s_table.data))) if distinct else s_table.data

        if order_by:
            s_table.order_by(order_by, desc)

        if isinstance(limit,str):
            s_table.data = [row for row in s_table.data if row is not None][:int(limit)]

        
        print("B+Tree used for select.")
        return s_table


    def _select_where_with_hash(self, return_columns, exthash, condition, distinct=False, order_by=None, desc=True, limit=None):  #!!! To be changed
        # if * return all columns, else find the column indexes for the columns specified
        if return_columns == '*':
            return_cols = [i for i in range(len(self.column_names))]
        else:
            return_cols = [self.column_names.index(colname) for colname in return_columns]

        column_name, operator, value = self._parse_condition(condition)

      
        # sequential search in case of range query which is not supported by Hash Index.
        rows = []
        if (operator == '<' or operator == '>' or operator == '<=' or operator == '>='):
            column = self.column_by_name(column_name)
            opsseq = 0
            for ind, x in enumerate(column):
                opsseq+=1
                if get_op(operator, x, value):
                    rows.append(ind)
        # using hashtable
        else: 
            index = exthash.get(value)
            rows.append(index)


        try:
            k = int(limit)
        except TypeError:
            k = None
        # same as simple select from now on
        rows = rows[:k]
        
        dict = {(key):([[self.data[i][j] for j in return_cols] for i in rows] if key=="data" else value) for key,value in self.__dict__.items()}

        dict['column_names'] = [self.column_names[i] for i in return_cols]
        dict['column_types']   = [self.column_types[i] for i in return_cols]

        s_table = Table(load=dict)

        s_table.data = list(set(map(lambda x: tuple(x), s_table.data))) if distinct else s_table.data

        if order_by:
            s_table.order_by(order_by, desc)

        if isinstance(limit,str):
            s_table.data = [row for row in s_table.data if row is not None][:int(limit)]

        return s_table


    def order_by(self, column_name, desc=True):
        '''
        Order table based on column.

        Args:
            column_name: string. Name of column.
            desc: boolean. If True, order_by will return results in descending order (False by default).
        '''
        column = [val if val is not None else 0 for val in self.column_by_name(column_name)]
        idx = sorted(range(len(column)), key=lambda k: column[k], reverse=desc)
        # print(idx)
        self.data = [self.data[i] for i in idx]
        # self._update()


    def _general_join_processing(self, table_right:Table, condition, join_type):
        '''
        Performs the processes all the join operations need (regardless of type) so that there is no code repetition.

        Args:
            condition: string. A condition using the following format:
                'column[<,<=,==,>=,>]value' or
                'value[<,<=,==,>=,>]column'.
                
                Operators supported: (<,<=,==,>=,>)
        '''
        # get columns and operator
        column_name_left, operator, column_name_right = self._parse_condition(condition, join=True)
        # try to find both columns, if you fail raise error

        if(operator != '=' and join_type in ['left','right','full']):
            class CustomFailException(Exception):
                pass
            raise CustomFailException('Outer Joins can only be used if the condition operator is "=".\n')

        try:
            column_index_left = self.column_names.index(column_name_left)
        except:
            raise Exception(f'Column "{column_name_left}" dont exist in left table. Valid columns: {self.column_names}.')

        try:
            column_index_right = table_right.column_names.index(column_name_right)
        except:
            raise Exception(f'Column "{column_name_right}" dont exist in right table. Valid columns: {table_right.column_names}.')

        # get the column names of both tables with the table name in front
        # ex. for left -> name becomes left_table_name_name etc
        left_names = [f'{self._name}.{colname}' if self._name!='' else colname for colname in self.column_names]
        right_names = [f'{table_right._name}.{colname}' if table_right._name!='' else colname for colname in table_right.column_names]

        # define the new tables name, its column names and types
        join_table_name = ''
        join_table_colnames = left_names+right_names
        join_table_coltypes = self.column_types+table_right.column_types
        join_table = Table(name=join_table_name, column_names=join_table_colnames, column_types= join_table_coltypes)

        return join_table, column_index_left, column_index_right, operator


    def _inner_join(self, table_right: Table, condition):
        '''
        Join table (left) with a supplied table (right) where condition is met.

        Args:
            condition: string. A condition using the following format:
                'column[<,<=,==,>=,>]value' or
                'value[<,<=,==,>=,>]column'.
                
                Operators supported: (<,<=,==,>=,>)
        '''
        join_table, column_index_left, column_index_right, operator = self._general_join_processing(table_right, condition, 'inner')

        # count the number of operations (<,> etc)
        no_of_ops = 0
        # this code is dumb on purpose... it needs to illustrate the underline technique
        # for each value in left column and right column, if condition, append the corresponding row to the new table
        for row_left in self.data:
            left_value = row_left[column_index_left]
            for row_right in table_right.data:
                right_value = row_right[column_index_right]
                if(left_value is None and right_value is None):
                    continue
                no_of_ops+=1
                if get_op(operator, left_value, right_value): #EQ_OP
                    join_table._insert(row_left+row_right)

        return join_table
    
    def _left_join(self, table_right: Table, condition):
        '''
        Perform a left join on the table with the supplied table (right).

        Args:
            condition: string. A condition using the following format:
                'column[<,<=,==,>=,>]value' or
                'value[<,<=,==,>=,>]column'.
                
                Operators supported: (<,<=,==,>=,>)
        '''
        join_table, column_index_left, column_index_right, operator = self._general_join_processing(table_right, condition, 'left')

        right_column = table_right.column_by_name(table_right.column_names[column_index_right])
        right_table_row_length = len(table_right.column_names)

        for row_left in self.data:
            left_value = row_left[column_index_left]
            if left_value is None:
                continue
            elif left_value not in right_column:
                join_table._insert(row_left + right_table_row_length*["NULL"])
            else:
                for row_right in table_right.data:
                    right_value = row_right[column_index_right]
                    if left_value == right_value:
                        join_table._insert(row_left + row_right)

        return join_table

    def _right_join(self, table_right: Table, condition):
        '''
        Perform a right join on the table with the supplied table (right).

        Args:
            condition: string. A condition using the following format:
                'column[<,<=,==,>=,>]value' or
                'value[<,<=,==,>=,>]column'.
                
                Operators supported: (<,<=,==,>=,>)
        '''
        join_table, column_index_left, column_index_right, operator = self._general_join_processing(table_right, condition, 'right')

        left_column = self.column_by_name(self.column_names[column_index_left])
        left_table_row_length = len(self.column_names)

        for row_right in table_right.data:
            right_value = row_right[column_index_right]
            if right_value is None:
                continue
            elif right_value not in left_column:
                join_table._insert(left_table_row_length*["NULL"] + row_right)
            else:
                for row_left in self.data:
                    left_value = row_left[column_index_left]
                    if left_value == right_value:
                        join_table._insert(row_left + row_right)

        return join_table
    
    def _full_join(self, table_right: Table, condition):
        '''
        Perform a full join on the table with the supplied table (right).

        Args:
            condition: string. A condition using the following format:
                'column[<,<=,==,>=,>]value' or
                'value[<,<=,==,>=,>]column'.
                
                Operators supported: (<,<=,==,>=,>)
        '''
        join_table, column_index_left, column_index_right, operator = self._general_join_processing(table_right, condition, 'full')

        right_column = table_right.column_by_name(table_right.column_names[column_index_right])
        left_column = self.column_by_name(self.column_names[column_index_left])

        right_table_row_length = len(table_right.column_names)
        left_table_row_length = len(self.column_names)
        
        for row_left in self.data:
            left_value = row_left[column_index_left]
            if left_value is None:
                continue
            if left_value not in right_column:
                join_table._insert(row_left + right_table_row_length*["NULL"])
            else:
                for row_right in table_right.data:
                    right_value = row_right[column_index_right]
                    if left_value == right_value:
                        join_table._insert(row_left + row_right)

        for row_right in table_right.data:
            right_value = row_right[column_index_right]

            if right_value is None:
                continue
            elif right_value not in left_column:
                join_table._insert(left_table_row_length*["NULL"] + row_right)

        return join_table

    def show(self, no_of_rows=None, is_locked=False):
        '''
        Print the table in a nice readable format.

        Args:
            no_of_rows: int. Number of rows.
            is_locked: boolean. Whether it is locked (False by default).
        '''
        output = ""
        # if the table is locked, add locked keyword to title
        if is_locked:
            output += f"\n## {self._name} (locked) ##\n"
        else:
            output += f"\n## {self._name} ##\n"

        # headers -> "column name (column type)"
        headers = [f'{col} ({tp.__name__})' for col, tp in zip(self.column_names, self.column_types)]
        if self.pk_idx is not None:
            # table has a primary key, add PK next to the appropriate column
            headers[self.pk_idx] = headers[self.pk_idx]+' #PK#'

        '''
        if self.unique_idx is not None:
            headers[self.unique_idx] = headers[self.unique_idx]+' #U#'
        '''

        if self.unique_idx is not None:
            # table has unique columns, add UQ next to the appropriate column
            for i in self.unique_idx:
               headers[i] = headers[i]+' #UQ#'

        # detect the rows that are no tfull of nones (these rows have been deleted)
        # if we dont skip these rows, the returning table has empty rows at the deleted positions
        non_none_rows = [row for row in self.data if any(row)]
        # print using tabulate
        print(tabulate(non_none_rows[:no_of_rows], headers=headers)+'\n')


    def _parse_condition(self, condition, join=False, notcheck=False):
        '''
        Parse the single string condition and return the value of the column and the operator.

        Args:
            condition: string. A condition using the following format:
                'column[<,<=,==,>=,>]value' or
                'value[<,<=,==,>=,>]column'.
                
                Operatores supported: (<,<=,==,>=,>)
            join: boolean. Whether to join or not (False by default).
        '''
        # if both_columns (used by the join function) return the names of the names of the columns (left first)
        if join:
            return split_condition(condition)

        if notcheck:
            left, op, right = split_condition(condition, True) #added a parameter to the split_condition method
        else:
            left, op, right = split_condition(condition)

        # cast the value with the specified column's type and return the column name, the operator and the casted value
        
        if left not in self.column_names:
            raise ValueError(f'Condition is not valid (cant find column name)')
        coltype = self.column_types[self.column_names.index(left)]

        return left, op, coltype(right)


    def _load_from_file(self, filename):
        '''
        Load table from a pkl file (not used currently).

        Args:
            filename: string. Name of pkl file.
        '''
        f = open(filename, 'rb')
        tmp_dict = pickle.load(f)
        f.close()

        self.__dict__.update(tmp_dict.__dict__)
