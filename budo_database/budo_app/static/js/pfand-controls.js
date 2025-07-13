$(document).ready(function() {
    // Handle pfand button clicks
    $('.pfand-btn').click(function() {
        const kidId = $(this).data('kid-id');
        const action = $(this).data('action');
        const button = $(this);
        
        // Disable button during request
        button.prop('disabled', true);
        
        // Prepare data for AJAX request
        const data = {
            id: kidId,
            action: action
        };
        
        // Make AJAX request
        $.ajax({
            url: '/update_pfand/',
            type: 'POST',
            data: JSON.stringify(data),
            contentType: 'application/json',
            success: function(response) {
                if (response.status === 'success') {
                    // Update the pfand count display
                    const pfandCountElement = $('#pfand-count');
                    pfandCountElement.text(response.new_pfand);
                    
                    // Update the taschengeld amount display
                    const taschengeldElement = $('#taschengeld-amount');
                    const remainingMoney = parseFloat(response.remaining_taschengeld);
                    
                    // Format the amount to 2 decimal places
                    let displayText = remainingMoney.toFixed(2);
                    
                    // Add alert emoji if amount is less than 5
                    if (remainingMoney < 5) {
                        displayText += ' 🚨';
                        taschengeldElement.addClass('alert');
                    } else {
                        taschengeldElement.removeClass('alert');
                    }
                    
                    taschengeldElement.text(displayText);
                    
                    // Disable decrease button if pfand is 0
                    if (response.new_pfand === 0) {
                        $('#decrease-pfand').prop('disabled', true);
                    } else {
                        $('#decrease-pfand').prop('disabled', false);
                    }
                } else {
                    alert('Error: ' + response.message);
                }
            },
            error: function(xhr, status, error) {
                alert('Error updating pfand: ' + error);
            },
            complete: function() {
                // Re-enable button
                button.prop('disabled', false);
            }
        });
    });
    
    // Initially disable decrease button if pfand is 0
    const currentPfand = parseInt($('#pfand-count').text().replace(' 🚨', ''));
    if (currentPfand === 0) {
        $('#decrease-pfand').prop('disabled', true);
    }
}); 