/** Utilities */
// http://stackoverflow.com/questions/1586341
$.fn.scrollView = function () {
  return this.each(function () {
    $('html, body').animate({
      scrollTop: $(this).offset().top - 30
    }, 750);
  });
};

// Serialize form data into object
// http://stackoverflow.com/questions/1184624
(function($) {
  $.fn.serializeObject = function() {
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
      if (o[this.name] !== undefined) {
        if (!o[this.name].push) {
          o[this.name] = [o[this.name]];
        }
        o[this.name].push(this.value || '');
      }
      else {
        o[this.name] = this.value || '';
      }
    });
    return o;
  };
})(jQuery);

/** Comments */
$('#phl-comment-submit').on('click', function(e) {
  e.preventDefault();
  var comment = {
    name: $('#phl-comment-name').val(),
    text: $('#phl-comment-text').val(),
    csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
  };
  $.post('/shift/comment/' + $('#phl-report-id').text() + '/',
      comment,
      function(data, textStatus, jqXHR) {
        $('#phl-comment-list').append($(data));
        $('#phl-comment-text').val('');
        $('#phl-comment-error-alert').fadeOut();
      })
    .fail(function(e) {
      $('#phl-comment-error-alert').fadeIn();
    });
});

/** Blocks */
(function($) {
  $.fn.phlcollapse = function() {
    var elem = this.parents('.phl-block')
    elem.find('.phl-field-table').toggle();
    elem.find('.phl-block-collapse').toggleClass('glyphicon-chevron-down glyphicon-chevron-right');
    return this;
  };
})(jQuery);

$(document).on('click', '.phl-block-collapse', function(e) {
  e.preventDefault();
  $(this).phlcollapse();
});

