'use client'; //needed to handle site events (clicks / events / interactions)

import React from "react";
import Image from "next/image";
import { Model } from "@/model";
import { filesSelectController } from "@/controllers";
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { send } from "process";
import router from "next/router";
import { motion } from "framer-motion";

const PORT = 8000;

const instance = axios.create({
  baseURL:
    "http://localhost:" + PORT.toString(),
});


export default function Home() {
  const router = useRouter();

  const [redraw, forceRedraw] = React.useState(0);
  const [requestData, setRequestData] = React.useState([]);

  function refresh() {
    forceRedraw(redraw + 1);
  }

  React.useEffect(() =>{
    instance
    .get("/ui/get-pending-requests")
    .then(function (response){
      setRequestData(response.data.incoming_requests)
    })
    .catch (function (error) {
      console.error("errored:", error)
    });
  }, [redraw]);

  function acceptRequest(req:any){
    const formData = new FormData();

    formData.append("peer_pub_key", req.peer_pub_key);
    formData.append("file", req.file);
    formData.append("send_method", req.upload_type);
    formData.append("size", req.size);
    formData.append("sha256", req.sha256);
    formData.append("date", req.date)

    instance
    .post("/ui/reupload-data", formData, {headers: {"Content-Type": "multipart/form-data",},})
    .then(function (response){
      // ...
    })
    .catch (function (error) {
      console.error("errored:", error)
    });

    refresh()
  }

  const SentRequestTable: React.FC = () => {
        return (
          <table className="w-full border-collapse border border-gray-300">
            <thead>
              <tr className="bg-gray-200">
              <th className="border p-2">Peer Pub Key</th>
              <th className="border p-2">Request Type</th>
              <th className="border p-2">File Name</th>
                <th className="border p-2">File Size</th>
                <th className="border p-2">File Hash</th>
                <th className="border p-2">Date</th>
                <th className="border p-2">Accept?</th>
              </tr>
            </thead>
            <tbody>
              {requestData.map((request) => (
                <tr key={request.date} className="hover:bg-gray-100">
                  <td className="border p-2">{request.peer_pub_key}</td>
                  <td className="border p-2">{request.isDirect ? "Direct" : "Universal"}</td>
                  <td className="border p-2">{request.filename}</td>
                  <td className="border p-2">{request.size_gb} Bytes</td>
                  <td className="border p-2">{request.sha256}</td>
                  <td className="border p-2">{request.date}</td>
                  <td>
                    <div className="button">Accept Request</div>
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
              <div className="titleText">Pending Incoming Requests</div>
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
      <div>This page represents incoming requests that have not yet been accepted</div>
      <div>
        <SentRequestTable/>
      </div>
    </div>  
    )
  }