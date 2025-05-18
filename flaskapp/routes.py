from flask import render_template, flash, redirect, url_for, request
from flaskapp import app, db
from flaskapp.models import BlogPost, IpView, Day, UkData
from flaskapp.forms import PostForm
import datetime

import pandas as pd
import json
import plotly
import plotly.express as px
import sqlalchemy

# --- Helper function to calculate vote shares ---
def get_vote_share_df(all_uk_data_objects):
    if not all_uk_data_objects:
        return pd.DataFrame()
    data_list = [{column.name: getattr(row, column.name) for column in UkData.__table__.columns} for row in all_uk_data_objects]
    df = pd.DataFrame(data_list)
    if df.empty or 'TotalVote19' not in df.columns: return df

    vote_cols_to_check = [f'{p}Vote19' for p in ['Con', 'Lab', 'LD', 'Green', 'Brexit', 'UKIP', 'SNP', 'PC']]
    for col in vote_cols_to_check + ['TotalVote19']:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
    df['TotalVote19'] = df['TotalVote19'].replace(0, pd.NA) # Avoid division by zero, treat 0 as NA for share calculation

    for party_prefix in ['Con', 'Lab', 'LD', 'Green', 'Brexit', 'UKIP', 'SNP', 'PC']:
        vote_col = f'{party_prefix}Vote19'
        share_col = f'{party_prefix}Vote19Share'
        if vote_col in df.columns:
            # Ensure TotalVote19 is not NA before division
            df[share_col] = df.apply(lambda row: (row[vote_col] / row['TotalVote19']) * 100 
                                     if pd.notna(row['TotalVote19']) and row['TotalVote19'] != 0 and pd.notna(row[vote_col]) 
                                     else pd.NA, axis=1)
    return df

# --- Standard Routes ---
@app.route("/")
@app.route("/home")
def home():
    posts = BlogPost.query.all()
    return render_template('home.html', posts=posts)

@app.route("/about")
def about():
    return render_template('about.html', title='About page')

@app.route("/post/new", methods=['GET', 'POST'])
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = BlogPost(title=form.title.data, content=form.content.data, user_id=1)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form)

@app.route('/dashboard')
def dashboard():
    days = Day.query.all()
    df_data = [{'Date': d.id, 'Page views': d.views} for d in days if d.id and d.views is not None]
    
    fig_title = "Page Views Per Day"
    if df_data:
        df = pd.DataFrame(df_data)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values(by='Date')
        fig = px.bar(df, x='Date', y='Page views', title=fig_title)
    else: 
        flash("No page view data available to display.", "info")
        fig = px.bar(title=f"{fig_title} - No Data Available") # Show empty chart with title
        
    fig.update_layout(title_x=0.5)
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('dashboard.html', title='Site Analytics: Page Views', graphJSON=graphJSON)

# --- Page 1: Interactive Scatter Plot ---
@app.route('/interactive_scatter', methods=['GET', 'POST'])
def interactive_scatter():
    page_title = "Interactive Scatter Plot: Census vs. Vote Share"
    all_uk_data = UkData.query.all()
    df_uk = get_vote_share_df(all_uk_data)

    # Define options for dropdowns
    census_vars = {
        'c11Retired': '% Retired (2011)', 
        'c11PopulationDensity': 'Pop Density (2011)', 
        'c11HouseOwned': '% House Owned (2011)',
        'c11FulltimeStudent': '% Full-time Students (2011)',
        'Turnout19': 'Turnout % (2019 GE)'
    }
    party_shares_all = {
        'ConVote19Share': 'Con Share', 'LabVote19Share': 'Lab Share', 
        'LDVote19Share': 'LD Share', 'GreenVote19Share': 'Green Share',
        'SNPVote19Share': 'SNP Share', 'PCVote19Share': 'PC Share',
        'BrexitVote19Share': 'Brexit Party Share'
    }
    color_vars_all = {'country': 'Country', 'region': 'Region'}

    if df_uk.empty:
        flash("No UK election data available for scatter plot.", "warning")
        return render_template('interactive_scatter.html', page_title=page_title, plot_title="Data Unavailable", graphJSON="{}",
                               census_vars=census_vars, party_shares={}, color_vars={},
                               selected_x=list(census_vars.keys())[0], selected_y=None, selected_color=None)

    # Filter options based on available and non-empty columns in df_uk
    valid_census_vars = {k: v for k, v in census_vars.items() if k in df_uk.columns and df_uk[k].notna().any()}
    valid_party_shares = {k: v for k, v in party_shares_all.items() if k in df_uk.columns and df_uk[k].notna().any()}
    valid_color_vars = {k: v for k, v in color_vars_all.items() if k in df_uk.columns and df_uk[k].notna().any()}
    
    selected_x = request.form.get('x_var', request.args.get('x_var', list(valid_census_vars.keys())[0] if valid_census_vars else None))
    selected_y = request.form.get('y_var', request.args.get('y_var', list(valid_party_shares.keys())[0] if valid_party_shares else None))
    selected_color = request.form.get('color_var', request.args.get('color_var', list(valid_color_vars.keys())[0] if valid_color_vars else ""))

    # Ensure selections are valid
    if selected_x not in valid_census_vars: selected_x = list(valid_census_vars.keys())[0] if valid_census_vars else None
    if selected_y not in valid_party_shares: selected_y = list(valid_party_shares.keys())[0] if valid_party_shares else None
    if selected_color != "" and selected_color not in valid_color_vars: selected_color = "" # Default to no color if invalid

    graphJSON = "{}"
    plot_title = "Select variables to plot"

    if selected_x and selected_y:
        # Prepare data for plotting
        columns_to_select = [selected_x, selected_y, 'constituency_name']
        if selected_color and selected_color in valid_color_vars: 
            columns_to_select.append(selected_color)
        
        df_plot = df_uk[columns_to_select].copy()
        # Ensure selected_x and selected_y are numeric for plotting
        for col in [selected_x, selected_y]: 
            if col in df_plot.columns:
                 df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')
        df_plot.dropna(subset=[selected_x, selected_y], inplace=True) # Drop rows where essential plot vars are NA

        if not df_plot.empty:
            plot_title = f"{valid_census_vars.get(selected_x, selected_x)} vs. {valid_party_shares.get(selected_y, selected_y)}"
            color_arg = selected_color if selected_color and selected_color in df_plot.columns else None
            
            fig = px.scatter(df_plot, x=selected_x, y=selected_y, color=color_arg,
                             hover_name='constituency_name',
                             labels={
                                 selected_x: valid_census_vars.get(selected_x, selected_x), 
                                 selected_y: valid_party_shares.get(selected_y, selected_y)
                             }) 
                             
            fig.update_layout(title_text='', title_x=0.5) 
            graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        else:
            plot_title = f"No valid data for {valid_census_vars.get(selected_x, selected_x)} vs. {valid_party_shares.get(selected_y, selected_y)}"
            flash(f"No valid data to plot for the selected combination: {plot_title}", "info")
    elif not selected_x or not selected_y:
        plot_title = "Please select both X and Y axis variables."
        flash("Please select variables for both X and Y axes for the scatter plot.", "warning")
    else: # Should not be reached if defaults are set from valid_..._vars
        plot_title = "Invalid variables selected."
        flash("One or both selected variables for the scatter plot are not available or invalid.", "warning")

    return render_template('interactive_scatter.html', page_title=page_title, plot_title=plot_title, graphJSON=graphJSON,
                           census_vars=valid_census_vars, party_shares=valid_party_shares, color_vars=valid_color_vars,
                           selected_x=selected_x, selected_y=selected_y, selected_color=selected_color)

# --- Page 2: Election Summaries ---
@app.route('/election_summaries', methods=['GET', 'POST'])
def election_summaries():
    page_title = "Election Summaries: National & Regional"
    all_uk_data = UkData.query.all()
    df_uk = get_vote_share_df(all_uk_data)

    if df_uk.empty:
        flash("No UK election data available for summaries.", "warning")
        return render_template('election_summaries.html', page_title=page_title, 
                               graphJSON_national_votes="{}", graphJSON_regional_shares="{}", graphJSON_regional_census="{}",
                               regions=[], selected_region="All UK", 
                               title_reg_shares="Regional Party Shares", title_reg_census="Regional Census Metrics")

    # National Vote Totals
    national_votes_cols = [f'{p}Vote19' for p in ['Con', 'Lab', 'LD', 'SNP', 'PC', 'Green', 'Brexit', 'UKIP'] if f'{p}Vote19' in df_uk.columns]
    national_totals_df = df_uk[national_votes_cols].sum(numeric_only=True).dropna()
    national_totals_df = national_totals_df[national_totals_df > 0].sort_values(ascending=False)
    if not national_totals_df.empty:
        national_totals_df.index = national_totals_df.index.str.replace('Vote19', '')
        fig_nat_votes = px.bar(national_totals_df, x=national_totals_df.index, y=national_totals_df.values, labels={'x':'Party', 'y':'Total National Votes'})
    else:
        fig_nat_votes = px.bar(title="National Vote Totals - No Data")
    fig_nat_votes.update_layout(title_text='National Vote Totals (2019 GE)', title_x=0.5)
    graphJSON_national_votes = json.dumps(fig_nat_votes, cls=plotly.utils.PlotlyJSONEncoder)

    # Regional Summaries
    regions = ["All UK"] + sorted(df_uk['region'].dropna().unique().tolist())
    selected_region = request.form.get('region_select', request.args.get('region_select', 'All UK'))
    if selected_region not in regions: selected_region = "All UK"

    df_focus = df_uk if selected_region == "All UK" else df_uk[df_uk['region'] == selected_region]
    
    graphJSON_regional_shares, graphJSON_regional_census = "{}", "{}"
    title_reg_shares = f"Avg Party Shares: {selected_region}"
    title_reg_census = f"Avg Census Metrics: {selected_region}"

    if not df_focus.empty:
        party_share_cols_all = [f'{p}Vote19Share' for p in ['Con', 'Lab', 'LD', 'SNP', 'PC', 'Green', 'Brexit']]
        party_share_cols_exist = [col for col in party_share_cols_all if col in df_focus.columns and df_focus[col].notna().any()]
        
        if party_share_cols_exist:
            avg_reg_shares = df_focus[party_share_cols_exist].mean().dropna()
            avg_reg_shares = avg_reg_shares[avg_reg_shares > 0.5].sort_values(ascending=False) 
            if not avg_reg_shares.empty:
                avg_reg_shares.index = avg_reg_shares.index.str.replace('Vote19Share', '')
                fig_reg_shares = px.bar(avg_reg_shares, x=avg_reg_shares.index, y=avg_reg_shares.values, labels={'x':'Party', 'y':'Avg. Share (%)'})
                fig_reg_shares.update_layout(title_text='', title_x=0.5)
                graphJSON_regional_shares = json.dumps(fig_reg_shares, cls=plotly.utils.PlotlyJSONEncoder)

        census_cols_map = {'c11Retired': '% Retired', 'c11PopulationDensity': 'Pop Density', 'c11HouseOwned': '% House Owned', 'Turnout19':'Turnout %'}
        census_cols_exist_keys = [k for k,v in census_cols_map.items() if k in df_focus.columns and df_focus[k].notna().any()]
        
        if census_cols_exist_keys:
            avg_reg_census = df_focus[census_cols_exist_keys].mean().dropna()
            if not avg_reg_census.empty:
                avg_reg_census.index = avg_reg_census.index.map(lambda x: census_cols_map.get(x,x))
                fig_reg_census = px.bar(avg_reg_census, x=avg_reg_census.index, y=avg_reg_census.values, labels={'x':'Metric', 'y':'Avg. Value'})
                fig_reg_census.update_layout(title_text='', title_x=0.5, xaxis_tickangle=-30)
                graphJSON_regional_census = json.dumps(fig_reg_census, cls=plotly.utils.PlotlyJSONEncoder)
            
    return render_template('election_summaries.html', page_title=page_title,
                           graphJSON_national_votes=graphJSON_national_votes,
                           regions=regions, selected_region=selected_region,
                           title_reg_shares=title_reg_shares, graphJSON_regional_shares=graphJSON_regional_shares,
                           title_reg_census=title_reg_census, graphJSON_regional_census=graphJSON_regional_census)

# --- before_request function ---
@app.before_request
def before_request_func():
    if request.blueprint == 'static' or request.path.startswith('/static/'): 
        return # Skip DB operations for static file requests
    try:
        day_id = datetime.date.today()
        client_ip = request.remote_addr
        
        current_day = Day.query.filter_by(id=day_id).first()
        if current_day:
            current_day.views += 1
        else:
            current_day = Day(id=day_id, views=1)
            db.session.add(current_day)
            
        ip_view_today = IpView.query.filter_by(ip=client_ip, date_id=day_id).first()
        if not ip_view_today:
            new_ip_view = IpView(ip=client_ip, date_id=day_id)
            db.session.add(new_ip_view)
            
        # Only commit if there are pending changes
        if db.session.dirty or db.session.new:
            db.session.commit()
            
    except sqlalchemy.exc.OperationalError as e:
        db.session.rollback() 
        app.logger.warning(f"DB lock or operational error in before_request for IP {request.remote_addr if request else 'Unknown'}: {e}")
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Unexpected error in before_request: {e}", exc_info=True)