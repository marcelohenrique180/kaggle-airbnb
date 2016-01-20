import numpy as np
import pandas as pd
from joblib import Parallel, delayed
import multiprocessing

from utils.preprocessing import one_hot_encoding
from utils.preprocessing import get_weekday
from utils.preprocessing import process_user_secs_elapsed
from utils.preprocessing import process_user_session

raw_data_path = '../data/raw/'
processed_data_path = '../data/processed/'

# Load raw data
train_users = pd.read_csv(raw_data_path + 'train_users.csv')
test_users = pd.read_csv(raw_data_path + 'test_users.csv')
sessions = pd.read_csv(raw_data_path + 'sessions.csv')

# Join users
users = pd.concat((train_users, test_users), axis=0, ignore_index=True)

# Drop date_first_booking column (empty since competition's restart)
users = users.drop('date_first_booking', axis=1)

# Replace NaNs
users['gender'].replace('-unknown-', np.nan, inplace=True)
users['language'].replace('-unknown-', np.nan, inplace=True)
sessions.replace('-unknown-', np.nan, inplace=True)

# Remove weird age values
users.loc[users['age'] > 100, 'age'] = np.nan
users.loc[users['age'] < 14, 'age'] = np.nan

# Change type to date
users['date_account_created'] = pd.to_datetime(users['date_account_created'])
users['date_first_active'] = pd.to_datetime(users['timestamp_first_active'],
                                            format='%Y%m%d%H%M%S')

users['weekday_account_created'] = users[
    'date_account_created'].apply(get_weekday)
users['weekday_first_active'] = users['date_first_active'].apply(get_weekday)

# Split dates into day, month, year
year_account_created = pd.DatetimeIndex(users['date_account_created']).year
users['year_account_created'] = year_account_created
month_account_created = pd.DatetimeIndex(users['date_account_created']).month
users['month_account_created'] = month_account_created
day_account_created = pd.DatetimeIndex(users['date_account_created']).day
users['day_account_created'] = day_account_created
year_first_active = pd.DatetimeIndex(users['date_first_active']).year
users['year_first_active'] = year_first_active
month_first_active = pd.DatetimeIndex(users['date_first_active']).month
users['month_first_active'] = month_first_active
day_first_active = pd.DatetimeIndex(users['date_first_active']).day
users['day_first_active'] = day_first_active

# Process session data
processed_sessions = Parallel(n_jobs=multiprocessing.cpu_count())(
    delayed(process_user_session)(
        user, sessions.loc[sessions['user_id'] == user])
    for user in sessions['user_id'].unique()
)
user_sessions = pd.DataFrame(processed_sessions).set_index('id')

# Joint the processed data with each user
users = users.set_index('id')
users = pd.concat([users, user_sessions], axis=1)

# TODO: Classify by dispositive

# Get the count of general session information
user_sessions = sessions.groupby('user_id').count()
user_sessions.rename(columns=lambda x: x + '_count', inplace=True)
users = pd.concat([users, user_sessions], axis=1)

processed_secs_elapsed = Parallel(n_jobs=multiprocessing.cpu_count())(
    delayed(process_user_secs_elapsed)(user, sessions.loc[
        sessions['user_id'] == user, 'secs_elapsed'])
    for user in sessions['user_id'].unique()
)
processed_secs_elapsed = pd.DataFrame(processed_secs_elapsed).set_index('id')

users = pd.concat([users, processed_secs_elapsed], axis=1)

train_users = train_users.set_index('id')
test_users = test_users.set_index('id')

processed_train_users = users.loc[train_users.index]
processed_test_users = users.loc[test_users.index]
processed_test_users.drop('country_destination', inplace=True, axis=1)

processed_train_users.to_csv(processed_data_path + 'processed_train_users.csv')
processed_test_users.to_csv(processed_data_path + 'processed_test_users.csv')

drop_list = [
    'date_account_created',
    'date_first_active',
    'timestamp_first_active'
]

# Drop columns
users = users.drop(drop_list, axis=1)

# TODO: Try with StandardScaler
# from sklearn.preprocessing import StandardScaler
# scaler = StandardScaler()
# scaler.fit_transform(users)

# Encode categorical features
categorical_features = [
    'gender', 'signup_method', 'signup_flow', 'language', 'affiliate_channel',
    'affiliate_provider', 'first_affiliate_tracked', 'signup_app',
    'first_device_type', 'first_browser', 'most_used_device'
]

users = one_hot_encoding(users, categorical_features)

users.index.name = 'id'
processed_train_users = users.loc[train_users.index]
processed_test_users = users.loc[test_users.index]
processed_test_users.drop('country_destination', inplace=True, axis=1)

processed_train_users.to_csv(processed_data_path + 'encoded_train_users.csv')
processed_test_users.to_csv(processed_data_path + 'encoded_test_users.csv')