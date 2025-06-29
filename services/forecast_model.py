import pandas as pd
from prophet import Prophet
from prophet.plot import plot_plotly
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from datetime import datetime, timedelta

def generate_forecast_plot(from_date=None, to_date=None):
    username = 'root'
    raw_password = 'Liyas@001'
    password = quote_plus(raw_password)
    host = 'localhost'
    port = 3306
    database = 'supply_chain_optimizer'

    engine = create_engine(f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{database}")

    try:
        if not from_date or not to_date:
            today = datetime.today().date()
            start_date = today - timedelta(days=365)
        else:
            start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
            today = datetime.strptime(to_date, "%Y-%m-%d").date()

        query = f"""
            SELECT 
                DATE_FORMAT(order_date, '%Y-%m-01') AS ds, 
                SUM(quantity) AS y
            FROM customerorders
            WHERE order_date BETWEEN '{start_date}' AND '{today}'
            GROUP BY ds
            ORDER BY ds;
        """

        df = pd.read_sql(query, engine)
        if df.empty:
            return None, "⚠️ No data available for forecasting.", []

        df['ds'] = pd.to_datetime(df['ds'])
        df['y'] = df['y'].astype(float)

        model = Prophet()
        model.fit(df)

        future = model.make_future_dataframe(periods=300)
        forecast = model.predict(future)

        fig = plot_plotly(model, forecast)
        forecast_html = fig.to_html(full_html=False)

        forecast['ds'] = pd.to_datetime(forecast['ds'])
        forecast_start = df['ds'].max() + timedelta(days=1)
        forecast_end = forecast_start + timedelta(days=300)

        monthly_forecast = forecast[(forecast['ds'] >= forecast_start) & (forecast['ds'] <= forecast_end)]
        monthly_forecast['month'] = monthly_forecast['ds'].dt.to_period('M')
        grouped = monthly_forecast.groupby('month')['yhat'].sum().reset_index()
        grouped['date'] = grouped['month'].astype(str)
        grouped['product'] = 'Total Orders'
        grouped['quantity'] = grouped['yhat'].round(2)

        result = grouped[['date', 'product', 'quantity']].to_dict('records')

        def summarize_forecast_data(forecast_df):
            summary = ""
            top_month = forecast_df.loc[forecast_df['quantity'].idxmax()]
            low_month = forecast_df.loc[forecast_df['quantity'].idxmin()]
            avg_quantity = forecast_df['quantity'].mean()
            summary += f"The highest demand is in {top_month['date']} with {top_month['quantity']} units.\n"
            summary += f"The lowest demand is in {low_month['date']} with {low_month['quantity']} units.\n"
            summary += f"On average, monthly demand is around {avg_quantity:.2f} units.\n"
            return summary

        forecast_summary = summarize_forecast_data(grouped)

        return forecast_html, None, result, forecast_summary

    except Exception as e:
        return None, f"Error generating forecast: {str(e)}", [], ""
