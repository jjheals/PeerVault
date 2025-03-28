'use client'; //needed to handle site events (clicks / events / interactions)

import React from "react";
import Image from "next/image";
import { useRouter } from 'next/navigation';
import axios from 'axios';

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
            </tr>
          </thead>
          <tbody>
            {requestData.map((request) => (
              <tr key={request.filename} className="hover:bg-gray-100">
                <td className="border p-2">{request.filename}</td>
                <td className="border p-2">{request.size_gb} Bytes</td>
                <td className="border p-2">{request.sha256}</td>
                <td className="border p-2">{request.date_shared}</td>
                <td className="border p-2">  
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    };

    return (
      <div className="header">
          <div className="header-row">
              <div className="titleText">Sent Requests</div>
          <div className="header-options-row">
              <div className="icon-padding"></div>
              <button onClick={()=> router.push("/")}>
                  <div className="hover" title="Return Home">
                      <Image
                          className="dark"
                          src="/home-1-svgrepo-com.svg"
                          alt="home icon"
                          width={50}
                          height={50}
                      />
                  </div>
              </button>
              <div className="icon-padding"></div>
          </div>
      </div>  
      <div>This page represents incoming requests</div>
      <div>
        <div>req: {requestData.filename}</div>
        <SentRequestTable/>
      </div>
    
    </div>  
    )
  }