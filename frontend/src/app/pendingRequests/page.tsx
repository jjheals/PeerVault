'use client'; //needed to handle site events (clicks / events / interactions)

import React from "react";
import { useRouter } from 'next/navigation';
import axios from 'axios';
import Image from "next/image";


const PORT = 8000;

const instance = axios.create({
  baseURL:
    "http://localhost:" + PORT.toString(),
});


export default function Home() {
  const router = useRouter();

  const [redraw, forceRedraw] = React.useState(0);
  const [requestData, setRequestData] = React.useState([]);
  
  React.useEffect(() =>{
    instance
    .get("/ui/get-sent-requests")
    .then(function (response){
      setRequestData(response.data["all_requests"])
    })
    .catch (function (error) {
      console.error("errored:", error)
    });
  }, [redraw]);

    const SentRequestTable: React.FC = () => {
          return (
            <table className="w-full border-collapse border border-gray-300">
              <thead>
                <tr className="bg-gray-200">
                <th className="border p-2">File Name</th>
                  <th className="border p-2">File Size</th>
                  <th className="border p-2">File Hash</th>
                  <th className="border p-2">Date</th>
                  <th className="border p-2">Resend</th>

                </tr>
              </thead>
              <tbody>
                {requestData.map((request) => (
                  <tr key={request.date_shared} className="hover:bg-gray-100">
                    <td className="border p-2 text-center">{request.filename}</td>
                    <td className="border p-2 text-center">{request.size_gb} Bytes</td>
                    <td className="border p-2 text-center">{request.sha256}</td>
                    <td className="border p-2 text-center">{request.date_shared}</td>
                    <td className="border p-2 text-center">
                      <a href={`/resend`} className="hover text-center" title="Resend Request">
                          <Image
                            className="dark"
                            src="/refresh.svg"
                            alt="History"
                            width={30}
                            height={30}
                          />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          );
        };
  }