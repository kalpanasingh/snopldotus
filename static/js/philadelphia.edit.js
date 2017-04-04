/** Editor */
var phl_enable_save = true;
var phl_editor_start_time = Date.now();

// Periodic reminders to add blocks which define a period
var reminders = [];

$('.phl-link-block-add').on('click', function(e) {
  e.preventDefault();
  var d = {
    report_id: $('#phl-report-id').text(),
    name: $(this).text(),
    csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
  };

  $.post('/shift/block', d,
      function(data, textStatus, jqXHR) {
        var elem = $(data.html);
        $('#phl-blocks').append(elem);
        $(elem).scrollView();
        $('#phl-alert-error-block-add').fadeOut();
        $('#phl-block-add-modal').modal('hide');
      })
    .fail(function(e) {
      $('#phl-alert-error-block-add').fadeIn();
    });
});

$('.phl-submit').on('click', function(e) {
  var overlay = $('<div style="position: fixed; margin: 0px; padding: 0px; height: 100%; width: 100%; z-index: 100000; background-color: white; opacity: 0.6; filter:alpha(opacity=60);"></div>').prependTo('body');
  if (confirm("Are you ready to submit this report?")) {
    // Save anything modified recently
    $('.phl-block-dirty').each(function(e) {
      $(this).save();
    });

    // Wait until no blocks are dirty
    while ($('.phl-block-dirty').length > 0);

    // Submit!
    $.ajax({
      url: '/shift/submit/' + $('#phl-report-id').text(),
      beforeSend: function(xhr, settings) {
        var csrftoken = $('input[name="csrfmiddlewaretoken"]').val();
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
      },
      type: 'POST',
      success: function(data, textStatus, jqXHR) {
        window.location.href = '/shift';
      },
      error: function(e) {
        alert('Error: Unable to submit report');
        overlay.remove();
      }
    });
  }
  else {
    overlay.remove();
  }
});

// "Insert timestamp" button
// We must track the state of the last focused text entry object since clicking
// the button steals the focus.
var last_focused_element = undefined;
var last_focused_element_selection_start = 0;
$(document).on('blur', 'input[type="text"]', function(e) {
  last_focused_element = $(this);
  last_focused_element_selection_start = last_focused_element[0].selectionStart;
});
$(document).on('blur', 'textarea', function(e) {
  last_focused_element = $(this);
  last_focused_element_selection_start = last_focused_element[0].selectionStart;
});
$('.phl-timestamp').on('click', function(e) {
  e.preventDefault();
  $.get('/shift/timestamp/',
      function(data, textStatus, jqXHR) {
        var text = last_focused_element.val();
        var pos = last_focused_element_selection_start;
        last_focused_element.val(text.substring(0, pos) + data + text.substring(pos) );
      })
    .fail(function(e) {
      toastr.error('Failed to fetch timestamp from server', 'Error');
    });
});

(function($) {
  $.fn.save = function(trample) {
    if (!trample) {
      trample = false;
    }
    var elem = this;
    var data = {
      id: elem.find('input[name="phl-block-id"]').val(),
      rev: elem.find('input[name="phl-block-rev"]').val(),
      editor_id: $('#phl-editor-id').text(),
      fields: [],
      csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val(),
      trample: trample
    };

    elem.find(".phl-field-form").each(function(i) {
      data.fields.push($(this).serializeObject());
    });
    data.fields = JSON.stringify(data.fields);

    elem.removeClass('phl-block-dirty');
    $.post('/shift/save',
        data,
        function(data, textStatus, jqXHR) {
          var elem = $('input[value="' + data.id + '"]').parents('.phl-block');
          elem.find('input[name="phl-block-rev"]').val(data.rev);
          elem.find('input[name="phl-block-editor-id"]').val($('#phl-editor-id').text());
        })
      .fail(function(e) {
        elem.addClass('phl-block-dirty');
        var id = elem.find('input[name="phl-block-id"]').val();
        toastr.error('Failed to save block ' + id + ' in database', 'Error');
      });
    return this;
  };
})(jQuery);

$(document).on('keyup', 'input[name="value"]', function(e) {
  $(this).parents('.phl-block').addClass('phl-block-dirty');
});

$(document).on('keyup', 'textarea', function(e) {
  $(this).parents('.phl-block').addClass('phl-block-dirty');
});

$(document).on('click', 'input[type="checkbox"]', function(e) {
  $(this).parents('.phl-block').addClass('phl-block-dirty');
});

(function($) {
  $.fn.lock = function() {
    this.find('.phl-field-table').hide();
    this.find('.phl-block-collapse')
      .removeClass('glyphicon-chevron-down glyphicon-chevron-right phl-block-collapse')
      .addClass('glyphicon-lock phl-block-locked')
      .attr('title', 'Unlock');
    this.find('.phl-block-delete').hide();
    return this;
  };
})(jQuery);

(function($) {
  $.fn.unlock = function() {
    this.find('.phl-block-locked')
      .removeClass('glyphicon-lock')
      .addClass('glyphicon-chevron-right phl-block-collapse')
      .attr('title', 'Collapse');
    this.find('.phl-block-delete').show();
    return this;
  };
})(jQuery);

$(document).on('click', '.glyphicon-lock', function(e) {
  e.preventDefault();
  var block_current = $(this).parents('.phl-block');
  var block_id = block_current.find('input[name="phl-block-id"]').val();
  $.get('/shift/block/' + block_id,
      function(data, textStatus, jqXHR) {
        block_current.replaceWith($(data.html));
        var elem = $('input[value="' + data.id + '"]').parents('.phl-block');
        elem.unlock().phlcollapse().save(true);
      })
    .fail(function(e) {
      toastr.error('Failed to unlock block in database', 'Error');
    });
});

$(document).on('click', '.phl-block-delete', function(e) {
  e.preventDefault();
  var block = $(this).parents('.phl-block');
  if (confirm("Are you sure you want to delete this block?")) {
    $.ajax({
      url: '/shift/delete/' + block.find('.phl-block-id').text(),
      beforeSend: function(xhr, settings) {
        var csrftoken = $('input[name="csrfmiddlewaretoken"]').val();
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
      },
      type: 'DELETE',
      success: function(data, textStatus, jqXHR) {
        block.remove();
      },
      error: function(e) {
        toastr.error('Failed to remove block from database', 'Error');
      }
    });
  }
});

$(function() {
  load_report();
  $('[data-toggle="tooltip"]').tooltip()
});

setInterval(function() {
  $('.phl-block-dirty').each(function(e) {
    if (phl_enable_save) {
      $(this).save();
    }
  });
  load_report();
  $('[data-toggle="tooltip"]').tooltip()
  check_reminders();
}, 5000);

function load_report() {
  var report_id = $('#phl-report-id').text();
  var editor_id = $('#phl-editor-id').text();

  $.get('/shift/view/' + report_id + '?json=true', function(data) {
    var editor_blocks = {};
    $('.phl-block').each(function(index, element) {
      var block_id = $(this).find('input[name="phl-block-id"]').val();
      var editor_id = $(this).find('input[name="phl-block-editor-id"]').val();
      editor_blocks[block_id] = editor_id;
    });

    var db_blocks = {};
    for (var i in data.blocks) {
      db_blocks[data.blocks[i].id] = data.blocks[i].value.editor_id;
    }

    for (db in db_blocks) {
      var dbi = db;
      var elem = $('input[value="' + dbi + '"]').parents('.phl-block');
      var e2 = elem.find('input[name="phl-block-editor-id"]').val(db_blocks[dbi]);
      if (!(db in editor_blocks)) {
        // in db, not report -- add it
        $.get('/shift/block/' + dbi,
          function(data, textStatus, jqXHR) {
            $('#phl-blocks').append($(data.html));
            var elem = $('input[value="' + dbi + '"]').parents('.phl-block');
            if (db_blocks[dbi] != editor_id) {
              elem.lock();
            }
          })
        .fail(function(e) {
          toastr.warning('Failed to fetch newly-created block from the database', 'Warning');
        });
      }
      else {
        if (db_blocks[dbi] && db_blocks[dbi] != editor_id) {
          elem.lock();
        }
        else if (elem.find('.phl-block-collapse').children('span').hasClass('glyphicon-lock')) {
          elem.unlock();
        }
      }
    }

    for (ebi in editor_blocks) {
      var elem = $('input[value="' + ebi + '"]').parents('.phl-block');
      if (!(ebi in db_blocks)) {
        // in report, not db -- remove it
        var title = elem.find('.phl-block-name').text();
        toastr.info('Removed block "' + title + '", which was deleted in another session.', 'Info');
        elem.remove();
      }
    }

    // Show any new comments
    var comment_timestamps = [];
    $(".phl-comment-created").each(function(i) {
      comment_timestamps.push($(this).text());
    });
    for (icomment in data.report.comments) {
      if ($.inArray(data.report.comments[icomment].created, comment_timestamps) == -1) {
          $.get('/shift/comment/' + data.report._id + '/' + icomment + '?json=true',
            function(data, textStatus, jqXHR) {
              $('#phl-comment-list').append($(data.html));
              if($("input[name=phl-notify-enable]").prop("checked")) {
                toastr.info('<i>' + data.text.substring(0, 20) + '...</i>', '<strong>' + data.name + '</strong> posted a new comment', { timeOut: 0, extendedTimeOut: 0});
              }
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

/** Fields */
$(document).on('click', '.phl-field-add', function(e) {
  e.preventDefault();
  var html = '<tr><td><a href="#"><span style="color: gray;" class="phl-field-delete ' +
             'glyphicon glyphicon-remove-circle"></span></a></td>' +
             '<td colspan="2" style="white-space: nowrap; vertical-align: top">' +
             '<form class="phl-field-form"><input type="text" class="form-control"' +
              'style="border-top: none; border-bottom: none; height: 3ex; ' +
              'margin-bottom: 0px; width: 25ex; display: inline" ' +
              'name="name" placeholder="Name">&nbsp;' +
             '<input type="hidden" name="type" value="text">' +
             '<input type="text" class="form-control"' +
              'style="border-top: none; border-bottom: none; height: 3ex; ' +
              'margin-bottom: 0px; width: 25ex; display: inline" ' +
              'name="value" placeholder="Value"></form></td>' +
             '</tr>';
  $(this).parents('.phl-field-table').find('tbody.phl-fields').append(html);
});

$(document).on('click', '.phl-field-delete', function(e) {
  e.preventDefault();
  $(this).parents('.phl-block').addClass('phl-block-dirty');
  $(this).parents('tr').remove();
});

$(document).on('click', '.phl-attachment-delete', function(e) {
  e.preventDefault();
  var elem = $(this).parents('tr');
  var block = $(this).parents('.phl-block');
  var block_id = block.find('input[name="phl-block-id"]').val();
  var block_rev = block.find('input[name="phl-block-rev"]').val();
  var name = elem.find('a.phl-attachment-name').text();
  $.ajax({
    url: '/shift/delete-attachment/' + block_id,
    type: 'POST',
    data: {
      name: name,
      rev: block_rev,
      csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
    },
    success: function(data, textStatus, jqXHR) {
      block.find('input[name="phl-block-rev"]').val(data.rev);
      elem.remove();
    }
  });
});

/** Attachments */
$(document).on('click', '.phl-attachment-add', function(e) {
  e.preventDefault();
  var block = $(this).parents('.phl-block');
  var block_id = block.find('input[name="phl-block-id"]').val();
  var block_rev = block.find('input[name="phl-block-rev"]').val();
  $('#phl-attachment-target-doc-id').val(block_id);
  $('#phl-attachment-target-doc-rev').val(block_rev);
  $('#phl-attachment-add-modal').modal('show');
});

$(document).on('click', '#phl-attachment-form-submit', function(e) {
  phl_enable_save = false;
  var form = $('#phl-attachment-form');
  var data = form.serializeObject();
  var doc_id = data.target_doc_id;
  data._attachments = $('#phl-attachment-file-field').val();
  if (data._attachments.length == 0) {
    $('#phl-alert-error-attachment-add').fadeIn();
    return;
  }
  $('#phl-alert-error-attachment-add').fadeOut();
  $(form).ajaxSubmit({
    target: $(form),
    url: '/shift/attachment/',
    type: 'post',
    dataType: 'json',
    clearForm: true,
    resetForm: true,
    beforeSubmit: function(data, jqForm, options) {
      return true;
    },
    success: function(data, textStatus, jqXHR, $form) {
      if (textStatus == 'success' || Number(textStatus) < 400) {
        var block = $('input[value="' + doc_id + '"]').parents('.phl-block');
        block.find('.phl-attachments').append($(data.html));
        block.find('input[name="phl-block-rev"]').val(data.rev);
        $('#phl-alert-error-attachment-add').fadeOut();
        $('#phl-attachment-add-modal').modal('hide');
        phl_enable_save = true;
      }
      else {
        $('#phl-alert-error-attachment-add').fadeIn();
      }
    }
  });

  load_report();
  return false;
});

function check_reminders() {
  $.each(reminders, function(i, o) {
    var nblocks = $('.phl-block[data-name="' + o.name + '"]').length;
    $('.phl-block[data-name="' + o.name + '"]').each(function(j) {
      var created = Date.parse($(this).attr('data-created'));
      o.times.add(created);
    });
    var max_time = Math.max.apply(null, Array.from(o.times));
    max_time = Math.max(max_time, phl_editor_start_time);
    if (Date.now() - max_time > o.period * 1000 * 60) {
      reminders[i].times.add(Date.now());
      if($("input[name=phl-reminders-enable]").prop("checked")) {
        toastr.warning('Complete "' + o.name + '"<br/>(posted ' + (new Date()).toLocaleString('en-US') + ')', 'Reminder (every ' + o.period + ' minutes)', { timeOut: 0, extendedTimeOut: 0});
      }
    }
  });
}

$(document).ready(function() {
  $("[name='phl-notify-enable']").bootstrapSwitch({
    onColor: 'success',
    size: 'mini',
    onText: '<span class="glyphicon glyphicon-bullhorn"></span>',
    offText: '<span class="glyphicon glyphicon-bullhorn"></span>'
  });
  $("[name='phl-reminders-enable']").bootstrapSwitch({
    onColor: 'success',
    size: 'mini',
    onText: '<span class="glyphicon glyphicon-time"></span>',
    offText: '<span class="glyphicon glyphicon-time"></span>'
  });
  $('[data-toggle="tooltip"]').tooltip()

  $('.phl-link-block-add').each(function(i, o) {
    var period = $(o).attr('data-period');
    if (period) {
      reminders.push({name: $(o).text(), period: period, times: new Set()});
    }
  });
});

