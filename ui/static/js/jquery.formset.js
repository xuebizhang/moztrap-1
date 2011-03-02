/**
 * jQuery Formset 1.1r14
 * @author Stanislaus Madueke (stan DOT madueke AT gmail DOT com)
 * @requires jQuery 1.2.6 or later
 *
 * Copyright (c) 2009, Stanislaus Madueke
 * All rights reserved.
 *
 * Licensed under the New BSD License
 * See: http://www.opensource.org/licenses/bsd-license.php
 */
;(function($) {
    $.fn.formset = function(opts)
    {
        var options = $.extend({}, $.fn.formset.defaults, opts),
            flatExtraClasses = options.extraClasses.join(' '),
            totalForms = $('#id_' + options.prefix + '-TOTAL_FORMS'),
            maxForms = $('#id_' + options.prefix + '-MAX_NUM_FORMS'),
            parent = $(this),
            $$ = $(this).children('li'),

            applyExtraClasses = function(row, ndx) {
                if (options.extraClasses) {
                    row.removeClass(flatExtraClasses);
                    row.addClass(options.extraClasses[ndx % options.extraClasses.length]);
                }
            },

            updateElementIndex = function(elem, prefix, ndx) {
                var idRegex = new RegExp('(' + prefix + '-(\\d+|__prefix__)-)'),
                    replacement = prefix + '-' + ndx + '-';
                if (elem.attr("for")) elem.attr("for", elem.attr("for").replace(idRegex, replacement));
                if (elem.attr('id')) elem.attr('id', elem.attr('id').replace(idRegex, replacement));
                if (elem.attr('name')) elem.attr('name', elem.attr('name').replace(idRegex, replacement));
            },

            hasChildElements = function(row) {
                return row.find('input,select,textarea,label').length > 0;
            },

            showAddButton = function() {
                return maxForms.length == 0 ||   // For Django versions pre 1.2
                    (maxForms.val() == '' || (maxForms.val() - totalForms.val() > 0));
            },

            insertDeleteLink = function(row) {
                $(options.deleteLink).appendTo(row).click(function() {
                    var row = $(this).parents('.' + options.formCssClass),
                        del = row.find('input:hidden[id $= "-DELETE"]'),
                        forms;
                    if (del.length) {
                        // We're dealing with an inline formset.
                        // Rather than remove this form from the DOM, we'll mark it as deleted
                        // and hide it, then let Django handle the deleting:
                        del.val('on');
                        row.hide();
                        forms = $('.' + options.formCssClass).not(':hidden');
                    } else {
                        row.remove();
                        // Update the TOTAL_FORMS count:
                        forms = $('.' + options.formCssClass).not('.formset-custom-template');
                        totalForms.val(forms.length);
                    }
                    // Apply extraClasses to form rows so they're nicely alternating.
                    // Also update names and IDs for all child controls, if this isn't a delete-able
                    // inline formset, so they remain in sequence.
                    for (var i=0, formCount=forms.length; i<formCount; i++) {
                        applyExtraClasses(forms.eq(i), i);
                        if (!del.length) {
                            forms.eq(i).find('input,select,textarea,label').each(function() {
                                updateElementIndex($(this), options.prefix, i);
                            });
                        }
                    }
                    // If a post-delete callback was provided, call it with the deleted form:
                    if (options.removed) options.removed(row);
                    return false;
                });
            };

        $$.each(function(i) {
            var row = $(this),
                del = row.find('input:checkbox[id $= "-DELETE"]');
            if (del.length) {
                // If you specify "can_delete = True" when creating an inline formset,
                // Django adds a checkbox to each form in the formset.
                // Replace the default checkbox with a hidden field:
                if (del.is(':checked')) {
                    // If an inline formset containing deleted forms fails validation, make sure
                    // we keep the forms hidden (thanks for the bug report and suggested fix Mike)
                    del.before('<input type="hidden" name="' + del.attr('name') +'" id="' + del.attr('id') +'" value="on" />');
                    row.hide();
                } else {
                    del.before('<input type="hidden" name="' + del.attr('name') +'" id="' + del.attr('id') +'" />');
                }
                // Hide any labels associated with the DELETE checkbox:
                $('label[for="' + del.attr('id') + '"]').hide();
                del.remove();
            }
            if (hasChildElements(row)) {
                row.addClass(options.formCssClass);
                if (row.is(':visible')) {
                    if (!options.deleteOnlyNew) {
                        insertDeleteLink(row);
                    }
                    applyExtraClasses(row, i);
                }
            }
        });

        var hideAddButton = !showAddButton(),
            addButton, template;
        // Clone the form template to generate new form instances:
        template = (options.formTemplate instanceof $) ? options.formTemplate : $(options.formTemplate);
        template.removeAttr('id').addClass(options.formCssClass + ' formset-custom-template');
        template.find('input,select,textarea,label').each(function() {
            updateElementIndex($(this), options.prefix, 2012);
        });
        insertDeleteLink(template);
        // FIXME: Perhaps using $.data would be a better idea?
        options.formTemplate = template;

        // Otherwise, insert it immediately after the last form:
        parent.after(options.addLink);
        addButton = parent.next();
        if (hideAddButton) addButton.hide();
        addButton.click(function() {
            var formCount = parseInt(totalForms.val()),
                row = options.formTemplate.clone(true).removeClass('formset-custom-template');
            applyExtraClasses(row, formCount);
            row.appendTo($(this).prev()).show();
            row.find('input,select,textarea,label').each(function() {
                updateElementIndex($(this), options.prefix, formCount);
            });
            totalForms.val(formCount + 1);
            // Check if we've exceeded the maximum allowed number of forms:
            if (!showAddButton()) $(this).hide();
            // If a post-add callback was supplied, call it with the added form:
            if (options.added) options.added(row);
            return false;
        });

        return $$;
    };

    /* Setup plugin defaults */
    $.fn.formset.defaults = {
        prefix: 'form',                  // The form prefix for your django formset
        formTemplate: null,              // The jQuery selection cloned to generate new form instances
        deleteLink: '<a class="delete-row" href="javascript:void(0)">remove</a>',
        addLink: '<a class="add-row" href="javascript:void(0)">add</a>',
        deleteOnlyNew: false,            // If true, only newly-added rows can be deleted
        formCssClass: 'dynamic-form',    // CSS class applied to each form in a formset
        extraClasses: [],                // Additional CSS classes, which will be applied to each form in turn
        added: null,                     // Function called each time a new form is added
        removed: null                    // Function called each time a form is deleted
    };
})(jQuery);
