// This Script allows to sort tables.

window.onload = function () {
    // Function to get the text content of a cell
    // function getCellValue(row, columnIdx) {
    //     return row.children[columnIdx].innerText || row.children[columnIdx].textContent;
    // }

    function getCellValue(row, columnIdx) {
        var cell = row.children[columnIdx];
        if (cell.classList.contains('zug-toggle')) {
            var switchElement = cell.querySelector('.switch');
            return switchElement.classList.contains('ja') ? 'ja' : 'nein';
        }
        return cell.innerText || cell.textContent;
    }

    // Function to compare two rows based on the text content of a specific column
    function rowComparer(columnIdx, ascending) {
        return function (rowA, rowB) {
            var cellValueA = getCellValue(ascending ? rowA : rowB, columnIdx);
            var cellValueB = getCellValue(ascending ? rowB : rowA, columnIdx);

            // If the cell values are numeric, compare them as numbers
            if (cellValueA !== '' && cellValueB !== '' && !isNaN(cellValueA) && !isNaN(cellValueB)) {
                return cellValueA - cellValueB;
            } else {
                // Otherwise, compare them as strings
                return cellValueA.toString().localeCompare(cellValueB);
            }
        }
    }

    // Get all the table headers
    var tableHeaders = document.querySelectorAll('th');

    // Add a click event listener to each table header
    tableHeaders.forEach(function (tableHeader) {
        tableHeader.addEventListener('click', function () {
            // Get the table that this header belongs to
            var table = tableHeader.closest('table');

            // Get the index of this header in the row
            var headerIdx = Array.from(tableHeader.parentNode.children).indexOf(tableHeader);

            // Get all the rows of the table, except for the first one (the header row)
            var rows = Array.from(table.querySelectorAll('tr:nth-child(n+2)'));

            // Sort the rows based on the content of the cells in this column
            var sortedRows = rows.sort(rowComparer(headerIdx, this.ascending = !this.ascending));

            // Append each sorted row back to the table
            sortedRows.forEach(function (row) {
                table.appendChild(row);
            });
        });
    });

    //This allows to click on a budo-family tag and filter the whole table for that specific family

    // Add a click event to all 'budo_family' cells
    $('.budo_family').click(function () {
        // Get the clicked 'budo_family' value
        var clickedValue = $(this).text();

        // Hide all rows
        $('.table_row').hide();

        // Show only the rows with the clicked 'budo_family' value
        $('.table_row').filter(function () {
            return $(this).find('.budo_family').text() === clickedValue;
        }).show();
    });
}