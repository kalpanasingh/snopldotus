/** Viewer */
$('#phl-report-delete').on('click', function(e) {
  var overlay = $('<div style="position: fixed; margin: 0px; padding: 0px; height: 100%; width: 100%; z-index: 100000; background-color: white; opacity: 0.6; filter:alpha(opacity=60);"></div>').prependTo('body');
  if (confirm("Are you sure you want to delete this report?")) {
    $.ajax({
      url: '/shift/delete/' + $('#phl-report-id').text(),
      beforeSend: function(xhr, settings) {
        var csrftoken = $('input[name="csrfmiddlewaretoken"]').val();
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
      },
      type: 'DELETE',
      success: function(data, textStatus, jqXHR) {
        window.location.href = '/shift';
      },
      error: function(e) {
        alert('Error: Unable to delete report');
      }
    });
  }
  else {
    overlay.remove();
  }
});

setInterval(function() {
  load_comments();
}, 5000);

// Show any new comments
function load_comments() {
  var report_id = $('#phl-report-id').text();
  $.get('/shift/view/' + report_id + '?json=true', function(data) {
    var comment_timestamps = [];
    $(".phl-comment-created").each(function(i) {
      comment_timestamps.push($(this).text());
    });
    for (icomment in data.report.comments) {
      if ($.inArray(data.report.comments[icomment].created, comment_timestamps) == -1) {
          $.get('/shift/comment/' + data.report._id + '/' + icomment + '?json=true',
            function(data, textStatus, jqXHR) {
              $('#phl-comment-list').append($(data.html));
              toastr.info('<i>' + data.text.substring(0, 20) + '...</i>', '<strong>' + data.name + '</strong> posted a new comment');
          })
        .fail(function(e) {
          toastr.warning('Failed to fetch new comment', 'Warning');
        });
      }
    }
  })
  .fail(function(e) {
    toastr.error('Failed to check report in database', 'Error');
  });
}

