const shimmer = "relative before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_2s_infinite] before:bg-gradient-to-r before:from-transparent before:via-gray-300 before:to-transparent";

function TableRow() {
  return (
    <tr className="border-b last-of-type:border-none">
      <td className="flex justify-center px-2 py-1">
        <div className="h-7"></div>
      </td>
    </tr>
  );
}

export function TableSkeleton() {
  return (
    <div className="bg-sand rounded-lg">
      <table className={`${shimmer} overflow-hidden table min-w-full rounded-lg`}>
        <tbody>
          <TableRow />
          <TableRow />
          <TableRow />
          <TableRow />
          <TableRow />
          <TableRow />
          <TableRow />
          <TableRow />
        </tbody>
      </table>
    </div>
  );
}