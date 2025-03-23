export default async function FileSummaryTable() {

  return (
    <div className="bg-sand rounded-lg">
      <table className="table min-w-full">
        <thead className="text-left border-b-2">
          <tr>
            <th scope="col" className="px-2 py-1">
              Recipient
            </th>
            <th scope="col" className="px-2 py-1">
              <div className="flex gap-1">
                Total Stored Remotely
              </div>
            </th>
            <th scope="col" className="px-2 py-1">
              <div className="flex gap-1">
                Total Stored Locally
              </div>
            </th>
            <th scope="col" className="px-2 py-1">
              <div className="flex gap-1">
                Total Shared
              </div>
            </th>
            <th scope="col" className="relative py-1 pr-3">
              <span className="sr-only">View</span>
            </th>
          </tr>
        </thead>
      </table>
    </div>
  );
}