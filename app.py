import pandas as pd
import plotly.graph_objects as go
from shiny import App, ui, render, reactive
from faicons import icon_svg
from shinywidgets import output_widget, render_plotly
import pathlib

df = pd.read_csv(pathlib.Path(__file__).parent / "supply.csv")



# Define UI
app_ui = ui.page_sidebar(
        ui.sidebar(
        ui.input_select("product_filter", "Product Type",
                        choices=["All"] + df["Product type"].dropna().unique().tolist(),
                        selected="All"),
        ui.input_select("location_filter", "Location",
                        choices=["All"] + df["Location"].dropna().unique().tolist(),
                        selected="All"),
    ),
    ui.layout_column_wrap(
        ui.value_box(
            "REVENUE",
            ui.output_ui("kpi_revenue"),
            showcase=ui.HTML(f'<span style="color: #6aaa96;">{icon_svg("dollar-sign", style="solid")}</span>'),
        ),
        ui.value_box(
            "PRODUCTS DELIVERED",
            ui.output_ui("products"),
            showcase=ui.HTML(f'<span style="color: #003f5c;">{icon_svg("truck", style="solid")}</span>'),
        ),
        ui.value_box(
            "DEFECTIVE PRODUCTS",
            ui.output_ui("defect"),
            showcase=ui.HTML(f'<span style="color: #e67f83;">{icon_svg("exclamation", style="solid")}</span>'),
        ),
        fill=False,
        height='100px'
    ),
    ui.card(
        ui.card_header("PROGRESS"),
        ui.row(
            ui.column(
                4,
                output_widget("inspection_progress", width="100%", height="250px"),
            ),
        ui.column(
            4,
            ui.card(
                ui.card_header("Stock Levels"),
                ui.tags.div(
                    ui.output_data_frame("pivot_table"),
                    style="""
                        font-size: 18px;
                        font-family: Arial, sans-serif;
                        padding: 2px;
                    """
                )
    , height='250px')
        ),
            ui.column(
                4,
                ui.layout_column_wrap(
                    ui.value_box(
                        "Average Lead Time",
                        ui.output_ui("avg_lead_time"),
                        showcase=ui.HTML(f'<span style="color: #003f5c;">{icon_svg("clock-rotate-left", style="solid")}</span>'),
                    ),
                    ui.value_box(
                        "Manufacturing Lead Time",
                        ui.output_ui("mfg_lead_time"),
                        showcase=ui.HTML(f'<span style="color: #003f5c;">{icon_svg("industry", style="solid")}</span>'),
                    ),
                    fillable=True
                ,width='100%')
            )
        ),
        fixed_width=True
    ),
    ui.row(
        ui.card(
            ui.card_header("SHIPMENT"),
                ui.layout_column_wrap(
                ui.column(8,
                          output_widget("cost_route_chart", height="300px",width='500px')),
                ui.column(4,output_widget("products_transport_chart", height="300px", width='500px')),
                fillable=True,
                    fill=True
            )
        )
    ),
    title=ui.tags.span(
        icon_svg("box"),
        "SUPPLY CHAIN DASHBOARD OVERVIEW"
    ),
    fillable=False
)

# Define server
def server(input, output, session):
    @reactive.calc
    def filtered_data():
        data = df.copy()
        if input.product_filter() != "All":
            data = data[data["Product type"] == input.product_filter()]
        if input.location_filter() != "All":
            data = data[data["Location"] == input.location_filter()]
        return data

    @output
    @render.ui
    def kpi_revenue():
        data = filtered_data()
        if data.empty:
            return ui.h3("No data")
        total = round(data["Revenue generated"].dropna().sum(), 0)
        return ui.h3(f"{total:,}")

    @output
    @render.ui
    def products():
        data = filtered_data()
        if data.empty:
            return ui.h3("No data")
        prod = data["Number of products sold"].dropna().sum()
        return ui.h3(f"{prod:,}")

    @output
    @render.ui
    def defect():
        data = filtered_data()
        if data.empty:
            return ui.h3("No data")
        defect = round(data["Defect rates"].dropna().mean(), 1)
        return ui.h3(f"{defect}%")

    @output
    @render_plotly
    def inspection_progress():
        data = filtered_data()
        if data.empty:
            return go.Figure()

        grouped = (
            data.dropna(subset=["Stock levels", "Inspection results"])
            .assign(Inspection_Result=data["Inspection results"].str.strip().str.lower())
            .groupby("Inspection_Result")["Stock levels"]
            .sum()
            .reset_index()
        )

        grouped = grouped.sort_values(by="Stock levels", ascending=True)
        labels = grouped["Inspection_Result"].tolist()
        values = grouped["Stock levels"].tolist()

        color_map = {
            "pass": "#6aaa96",
            "fail": "#e67f83",
            "pending": "orange"
        }
        colors = [color_map.get(label, "gray") for label in labels]
        total_stock = sum(values)

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.7,
            textinfo="value+label",
            textposition="outside",
            marker=dict(colors=colors)
        )])

        fig.update_layout(
            title=dict(
                text="Inspection",
                font_size=20,
                x=0.5,
                xanchor="center"
            ),
            annotations=[dict(
                text=f"<b>{int(total_stock)}</b><br>Stock Levels",
                x=0.5,
                y=0.5,
                font_size=18,
                showarrow=False
            )],
            showlegend=False,
            height=250,
            margin=dict(t=60, b=10, l=10, r=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig

    @output
    @render.ui
    def avg_lead_time():
        data = filtered_data()
        if data.empty or "Lead times" not in data.columns:
            return ui.h3("N/A")
        avg = round(data["Lead times"].dropna().mean(), 1)
        return ui.h3(f"{avg} days")

    @output
    @render.ui
    def mfg_lead_time():
        data = filtered_data()
        if data.empty or "Manufacturing lead time" not in data.columns:
            return ui.h3("N/A")
        mfg = round(data["Manufacturing lead time"].dropna().mean(), 1)
        return ui.h3(f"{mfg} days")

    @output
    @render.data_frame
    def pivot_table():
        data = filtered_data()
        if data.empty:
            return pd.DataFrame()

        pivot = pd.pivot_table(
            data,
            index="Product type",
            columns="Inspection results",
            values="Stock levels",
            aggfunc="sum",
            fill_value=0
        )

        pivot.columns.name = None
        return pivot.reset_index()

    @output
    @render_plotly
    def cost_route_chart():
        data = filtered_data()
        if data.empty:
            return go.Figure()

        grouped = data.groupby("Routes")["Costs"].sum().reset_index()
        grouped = grouped.sort_values(by="Costs", ascending=True)

        fig = go.Figure(go.Bar(
            y=grouped["Routes"],
            x=grouped["Costs"],
            marker_color=grouped['Costs'],
            orientation='h',
            marker=dict(cornerradius="30%", colorscale="darkmint")
        ))

        fig.update_layout(
            title=dict(
                text="Total Cost Routes",
                font_size=20,
                x=0.5,
                xanchor="center"
            ),
            xaxis_title=None,
            yaxis_title=None,
            height=275,
            margin=dict(t=60, b=10, l=10, r=10),
            bargap=0.4,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig

    @output
    @render_plotly
    def products_transport_chart():
        data = filtered_data()
        if data.empty:
            return go.Figure()

        grouped = data.groupby("Transportation modes")["Number of products sold"].sum().reset_index()
        grouped = grouped.sort_values(by="Number of products sold", ascending=False)

        fig = go.Figure(go.Bar(
            x=grouped["Transportation modes"],
            y=grouped["Number of products sold"],
            marker_color=grouped['Number of products sold'],
            marker=dict(cornerradius="30%", colorscale="darkmint"),
            orientation="v"
        ))

        fig.update_layout(
            title=dict(
                text="Transportation",
                font_size=20,
                x=0.5,
                xanchor="center"
            ),
            xaxis_title=None,
            yaxis_title=None,
            height=275,
            margin=dict(t=60, b=10, l=10, r=10),
            bargap=0.4,
            width=500,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig


# Run app
app = App(app_ui, server)
app.run()
