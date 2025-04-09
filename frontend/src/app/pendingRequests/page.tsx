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
    .get("/ui/get-universal-requests")
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
                    <td className="border p-2">{request.filename}</td>
                    <td className="border p-2">{request.size_gb} Bytes</td>
                    <td className="border p-2">{request.sha256}</td>
                    <td className="border p-2">{request.date_shared}</td>
                    <td className="border p-2">
                      <a href={`/resend`} className="hover" title="Resend Request">
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

    return (
      <div className="header">
          <div className="header-row">
              <div className="titleText">Universal Pending Requests</div>
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
      <div>This page is representing the requests sent out without a specific recipient in mind</div>
      <div>
        <SentRequestTable/>
      </div>
    </div>  
    )
  }