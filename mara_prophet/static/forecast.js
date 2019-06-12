function showQueryDetails(url) {
    // $('#query-details').empty().append(spinner());
    loadContentAsynchronously('query-details', url);
    $('#query-details-dialog').modal();
}

/** downloads the current query as CSV file */
function downloadCSV(query_id, metric_name, chart_title) {
    $('#download-csv-dialog input[name=query_id]').val(query_id);
    $('#download-csv-dialog input[name=metric_name]').val(dashboard_title);
    $('#download-csv-dialog input[name=chart_title]').val(chart_title);
    $('#download-csv-dialog').modal();
}
