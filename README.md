## About volfeed

Volfeed is an ingestion pipeline for Deribit's Bitcoin option chain data, your Deribit account summary, and BTC prices. The script will capture the data at the interval of your choice and put it Timescaledb. In addition to data provided by Deribit's get_book_summary_by_currency you will get all IVs as well (calculated using py_lets_be_rational). A VM with 2GB RAM and 25GB of storage would handle this nicely.

## How to setup the pipeline

### Install Timescaledb using Docker

First we need a Timescaledb database, we'll use the official Docker image

    docker pull timescale/timescaledb:pg14

Then start an instance, remember to change 'password' with your password

    docker run -d --name timescaledb -p 5432:5432 \
    -v timescaledb-data:/var/lib/postgresql/data \
    -e POSTGRES_PASSWORD=password timescale/timescaledb:pg14

### Create the databases and tables

Connect to your Timescale instance and start doing some sql work, using psql, you can do this:

    psql -U postgres -h localhost

You will want two identical databases, one for production and one for development. Note that i'm using my server's instance to house both the production and the development database, you can separate them but be sure to config the parameters.yaml file and the .env file accordingly.

    CREATE DATABASE dev_option_chain;
    CREATE DATABASE option_chain;

Now connect to each of the database and start creating the necessary tables. For example, connect to the option_chain db:

    \c option_chain

Create the btc_option table:

    CREATE TABLE public.btc_option (
        currency TEXT NOT NULL,
        expiry_date TIMESTAMP with time zone NOT NULL,
        strike DOUBLE PRECISION NOT NULL,
        option_type TEXT NOT NULL,
        mid_price DOUBLE PRECISION,
        ask_price DOUBLE PRECISION,
        mark_price DOUBLE PRECISION,
        bid_price DOUBLE PRECISION,
        delta DOUBLE PRECISION,
        net_delta DOUBLE PRECISION,
        vega DOUBLE PRECISION,
        theta DOUBLE PRECISION,
        gamma DOUBLE PRECISION,
        underlying_price DOUBLE PRECISION,
        iv DOUBLE PRECISION,
        creation_timestamp TIMESTAMP with time zone NOT NULL,
        time TIMESTAMP with time zone NOT NULL default current_timestamp
    );

Create the btc_account_summary table:

    CREATE TABLE public.btc_account_summary (
        equity DOUBLE PRECISION,
        balance DOUBLE PRECISION,
        futures_pl DOUBLE PRECISION,
        options_pl DOUBLE PRECISION,
        initial_margin DOUBLE PRECISION,
        maintenance_margin DOUBLE PRECISION,
        options_delta DOUBLE PRECISION,
        delta_total DOUBLE PRECISION,
        options_vega DOUBLE PRECISION,
        options_theta DOUBLE PRECISION,
        options_gamma DOUBLE PRECISION,
        time TIMESTAMP with time zone NOT NULL default current_timestamp
    );

Create the btc_price table:

    CREATE TABLE public.btc_price (
        index_price DOUBLE PRECISION,
        time TIMESTAMP with time zone NOT NULL default current_timestamp
    );

Set up the hypertables and the compression policies, replace the your_table and run these commands for each of the tables you created above. **Remember to do this before you run the Python app to insert data to it, it won't let you run this if the table already contains any data**:

    SELECT create_hypertable('your_table', by_range('time', INTERVAL '7 day'));
    ALTER TABLE your_table SET (timescaledb.compress, timescaledb.compress_segmentby = 'expiry_date', timescaledb.compress_orderby = 'time DESC');
    SELECT add_compression_policy('your_table', compress_after => INTERVAL '1h');

### Setup parameters.yaml

The code is designed for a local and a production environment, edit the parameters.yaml file for your needs, using the databases we created above, the file should look like this:

    production:
        db_name: # the name of the production db
        update_interval: 300 # number of seconds between each update
    development:
        db_name: # the name of the development db
        update_interval: 30 # number of seconds between each update

### Setup .env

On your local environment, the .env file should look like this:

    DERIBIT_CLIENT_ID=YOUR_DERIBIT_CLIENT_ID
    DERIBIT_CLIENT_SECRET=YOUR_READ_ONLY_DERIBIT_CLIENT_SECRET
    CONNECTION=postgres://postgres:YOUR_POSTGRES_PASSWORD@YOUR_DOMAIN_OR_IP:5432/
    MODE=development

On your production environment, it should look like this:

    DERIBIT_CLIENT_ID=YOUR_DERIBIT_CLIENT_ID
    DERIBIT_CLIENT_SECRET=YOUR_READ_ONLY_DERIBIT_CLIENT_SECRET
    CONNECTION=postgres://postgres:YOUR_POSTGRES_PASSWORD@YOUR_DOMAIN_OR_IP:5432/
    MODE=production

**The .env file is ignored in .gitignore, so you will have to create it on your production server manually**
**Note you only need view permission for the deribit credentials**

### Install the python libraries

At the root folder of the app, we install the lib requirements:

    pip install -r requirements.txt

### Start the data pipeline

To start the data pipeline we simply do:

    python main.py

Observe the logs, you can use Ctrl+C to stop the pipeline, it'll exit gracefully by closing all the connection pool and deribit session.

To run the app as a background service, you can use PM2 to start the app instead
First install pm2, assuming you have node and npm already:

    npm install pm2 -g

Then start the app with pm2, replace your_pipeline with a name of your choosing:

    pm2 start main.py --name your_pipeline
