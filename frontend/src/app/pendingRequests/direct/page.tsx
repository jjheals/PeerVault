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

    return (
      <div className="header">
          <div className="header-row">
              <div className="titleText">Direct Requests</div>
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
    </div>  
    )
  }