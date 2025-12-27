
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': [''],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
        'api_crawl',
        default_args=default_args,
        max_active_runs=1,
        description='API Crawler for HackerNews & Dev.to',
        schedule_interval="0 * * * *",  # Hourly
        start_date=days_ago(0),
        tags=['NewsBot', 'API'],
) as dag:

    t1 = BashOperator(
        task_id='start',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_start.py --start {{ ds }} --prefix=./run',
    )

    t2 = BashOperator(
        task_id='prepare',
        bash_command='mkdir -p ~/airflow/data/news/{{ run_id }}',
    )

    t3 = BashOperator(
        task_id='pull',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_pull.py '
                     '--start {{ ds }} '
                     '--prefix=./run '
                     '--run-id={{ run_id }} '
                     '--job-id={{ ti.job_id }} '
                     '--data-folder="data/news" '
                     '--sources=APICrawler',
    )

    t4 = BashOperator(
        task_id='save',
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_save.py '
                     '--start {{ ds }} '
                     '--prefix=./run '
                     '--run-id={{ run_id }} '
                     '--job-id={{ ti.job_id }} '
                     '--data-folder="data/news" '
                     '--targets={{ dag_run.conf.setdefault("targets", "notion") }} '
                     '--dedup={{ dag_run.conf.setdefault("dedup", True) }} '
                     '--sources=APICrawler',
    )

    t5 = BashOperator(
        task_id='finish',
        depends_on_past=False,
        bash_command='cd ~/airflow/run/auto-news/src && python3 af_end.py '
                     '--start {{ ds }} '
                     '--prefix=./run ',
    )

    t1 >> t2 >> t3 >> t4 >> t5
