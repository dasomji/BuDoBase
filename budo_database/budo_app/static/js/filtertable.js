// This Script allows to sort tables.

window.onload = function () {
    // Function to get the text content of a cell
    function getCellValue(row, columnIdx) {
        return row.children[columnIdx].innerText || row.children[columnIdx].textContent;
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
}